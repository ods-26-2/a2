"""Testes do A2 Local. Sem Kafka, catraca ou VPS reais."""
import sqlite3
import tempfile
import threading
import unittest
import uuid
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from fastapi import HTTPException

import acessos_api as api
import database
import interpreta_codigo as qr
import regras_entrada as regras
import liberar as a2
from s4_client import S4Client


CPF = '12345678909'  # CPF sintético de teste
CHAVE = 'a' * 32
AGORA = 1767268800
UTC = '2026-01-01T12:00:00.000Z'
ID = str(uuid.UUID(int=1))


def gerar_qr(inicio, fim, cpf_base=123456789, mascara=0b101):
    """Gera um bloco AES-256 de teste com o layout fornecido ao A2."""
    bruto = (cpf_base.to_bytes(4, 'big') + inicio.to_bytes(4, 'big')
             + fim.to_bytes(4, 'big') + bytes([mascara, 0, 0, 0]))
    enc = Cipher(algorithms.AES(CHAVE.encode('ascii')), modes.ECB()).encryptor()
    return (enc.update(bruto) + enc.finalize()).hex()


class TestValidacaoQR(unittest.TestCase):
    def setUp(self):
        p = patch.dict('os.environ', {'A2_AES_KEY': CHAVE})
        p.start()
        self.addCleanup(p.stop)

    def test_descriptografia_e_cpf(self):
        codigo = gerar_qr(AGORA - 60, AGORA + 60)
        dados = qr.decodifica_codigo(codigo)
        self.assertEqual(dados['cpf'], CPF)
        self.assertEqual(dados['start_timestamp'], AGORA - 60)
        self.assertEqual(dados['end_timestamp'], AGORA + 60)
        self.assertEqual(dados['allowed_days'], [0, 2])

    def test_formatos_hex_bytes_latin1(self):
        codigo = gerar_qr(AGORA - 60, AGORA + 60)
        bruto = bytes.fromhex(codigo)
        for entrada in [codigo, bruto, bruto.decode('latin-1')]:
            with self.subTest(tipo=type(entrada)):
                self.assertEqual(qr.decodifica_codigo(entrada)['cpf'], CPF)

    @patch.object(regras.time, 'time', return_value=AGORA)
    def test_codigo_valido_e_limites_inclusivos(self, _):
        for inicio, fim in [(AGORA - 1, AGORA + 1), (AGORA, AGORA + 1), (AGORA - 1, AGORA)]:
            with self.subTest(inicio=inicio, fim=fim):
                self.assertEqual(regras.liberar_entrada(gerar_qr(inicio, fim)), (True, CPF))

    @patch.object(regras.time, 'time', return_value=AGORA)
    def test_codigo_expirado(self, _):
        self.assertEqual(regras.liberar_entrada(gerar_qr(AGORA-20, AGORA-1)), (False, CPF))

    @patch.object(regras.time, 'time', return_value=AGORA)
    def test_codigo_ainda_nao_valido(self, _):
        self.assertEqual(regras.liberar_entrada(gerar_qr(AGORA+1, AGORA+20)), (False, CPF))

    def test_payload_invalida(self):
        for codigo in ('invalido', '', gerar_qr(AGORA+1, AGORA)):
            with self.subTest(codigo=codigo):
                self.assertEqual(regras.liberar_entrada(codigo), (False, None))

    def test_chave_com_tamanho_invalido(self):
        with patch.dict('os.environ', {'A2_AES_KEY': 'curta'}):
            with self.assertRaises(ValueError):
                qr.decodifica_codigo(gerar_qr(AGORA-1, AGORA+1))


class TestKafkaA2(unittest.TestCase):
    def evento(self):
        return dict(message_type='event', schema='ods.i6.code_read', schema_version='1.0',
                    producer='I6', source_id='imx519', captured_at=UTC, message_id=ID,
                    payload=dict(frame_index=7, code_type='QR_CODE', decoded_data='teste', bbox=[0, 0, 10, 10]))

    def test_evento_valido_encaminhado(self):
        controller, s4 = Mock(), Mock()
        a2.process_kafka_message(self.evento(), controller, s4)
        controller.receive_qr.assert_called_once_with(source_id='imx519', decoded_data='teste',
                         captured_at=UTC, frame_index=7, message_id=ID)

    def test_evento_invalido_ignorado(self):
        for mudancas in [dict(producer='outro'), dict(schema_version='2.0'),
                        dict(source_id=''), dict(captured_at=''), dict(payload=None),
                        dict(payload={'frame_index': -1, 'decoded_data': 'teste'})]:
            with self.subTest(mudancas=mudancas):
                controller = Mock()
                a2.process_i6_event(dict(self.evento(), **mudancas), controller)
                controller.receive_qr.assert_not_called()

    def controlador(self):
        # Instancia apenas os atributos usados no roteamento, sem iniciar threads.
        c = a2.AccessController.__new__(a2.AccessController)
        c.dedup_lock = threading.Lock()
        c.recent_events = {}
        c.logical_mapping = {'imx519': {'turnstile_id': 'catraca-01'}}
        c.controllers = {'catraca-01': Mock()}
        return c

    def test_deduplicacao_por_message_id(self):
        c = self.controlador()
        with patch.object(a2, 'KAFKA_DEDUP_TTL', 60), patch.object(a2.time, 'monotonic', return_value=100):
            for _ in range(2):
                c.receive_qr('imx519', 'teste', UTC, 7, ID)
            c.controllers['catraca-01'].add_qr.assert_called_once_with('teste', 'imx519', UTC, 7, ID)
            c.receive_qr('imx519', 'teste', UTC, 8, 'outro-id')
            self.assertEqual(c.controllers['catraca-01'].add_qr.call_count, 2)

    def test_camera_sem_mapeamento(self):
        c = self.controlador()
        c.receive_qr('desconhecida', 'teste', UTC, 7, ID)
        c.controllers['catraca-01'].add_qr.assert_not_called()


class FimDoCiclo(Exception):
    """Interrompe a repetição do worker após um único evento de teste."""


class TestCatraca(unittest.TestCase):
    def executar_ciclo(self, status='passed', sentido='entrada', valido=True, online=True,
                        idade=0, falha=False):
        driver, registry, logger, s4 = Mock(), Mock(), Mock(), Mock()
        # Não inicia os workers reais; executa process() por um ciclo.
        with patch.object(a2.threading.Thread, 'start'):
            c = a2.TurnstileController('catraca-01', driver, {}, registry, 2, logger, s4, 5)
        if online:
            c.online_event.set()
        driver.wait_for_passage.return_value = dict(status=status, direction=sentido)
        if falha:
            driver.release.side_effect = OSError('offline')
        s4.request_snapshot.return_value = ID
        s4.get_evidence.return_value = {'media_status': 'READY'}
        evento = dict(decoded_data='teste', source_id='imx519', captured_at=UTC,
                      frame_index=7, message_id=ID, received_at=100-idade)
        with patch.object(c, 'take_latest', side_effect=[evento, FimDoCiclo]), \
             patch.object(a2, 'liberar_entrada', return_value=(valido, CPF)), \
             patch.object(a2.time, 'monotonic', return_value=100):
            with self.assertRaises(FimDoCiclo):
                c.process()
        return c, driver, logger, s4

    def test_passagem_confirmada_registra(self):
        for sentido in ('entrada', 'saida'):
            with self.subTest(sentido=sentido):
                _, driver, logger, s4 = self.executar_ciclo(sentido=sentido)
                driver.release.assert_called_once()
                s4.request_snapshot.assert_called_once_with(source_id='imx519', captured_at=UTC, cpf=CPF)
                logger.register.assert_called_once_with(cpf=CPF, direction=sentido, source_id='imx519',
                    turnstile_id='catraca-01', i6_message_id=ID, frame_index=7, captured_at=UTC,
                    evidence={'media_status': 'READY'})

    def test_timeout_desistencia_e_sentido_desconhecido_sem_log(self):
        for status, sentido in [('timeout', None), ('give_up', None), ('passed', 'outro')]:
            with self.subTest(status=status, sentido=sentido):
                _, driver, logger, _ = self.executar_ciclo(status=status, sentido=sentido)
                driver.release.assert_called_once()
                logger.register.assert_not_called()

    def test_invalido_offline_e_qr_antigo_nao_liberam(self):
        for opcoes in [dict(valido=False), dict(online=False), dict(idade=3)]:
            with self.subTest(opcoes=opcoes):
                _, driver, logger, s4 = self.executar_ciclo(**opcoes)
                driver.release.assert_not_called()
                logger.register.assert_not_called()
                s4.request_snapshot.assert_not_called()

    def test_falha_na_liberacao_marca_offline(self):
        c, driver, logger, _ = self.executar_ciclo(falha=True)
        self.assertFalse(c.online)
        driver.wait_for_passage.assert_not_called()
        logger.register.assert_not_called()

    def test_reconexao(self):
        driver, registry = Mock(), Mock()
        with patch.object(a2.threading.Thread, 'start'):
            c = a2.TurnstileController('catraca-01', driver, {}, registry, 2, Mock(), Mock(), 5)
        driver.initialize.side_effect = [OSError('offline'), None]
        with self.assertRaises(OSError):
            c.try_connect()
        self.assertFalse(c.online)
        c.try_connect()
        self.assertTrue(c.online)
        registry.register.assert_called_once_with(driver)

    def test_s4_simulado(self):
        with patch.dict('os.environ', {'TESTE_S4': 'true'}):
            client = S4Client(Mock())
            req = client.request_snapshot('imx519', UTC, CPF)
            evidencia = client.get_evidence(req)
            self.assertEqual(evidencia['media_status'], 'READY')
            self.assertTrue(evidencia['media_uri'].startswith('teste-s4://'))
            self.assertIsNone(client.producer)


class TestBancoAPIeNuvem(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / 'testes.db'
        for modulo in (api, a2):
            p = patch.object(modulo, 'DATABASE_FILE', self.db)
            p.start()
            self.addCleanup(p.stop)
        self.logger = a2.AccessLogger()
        self.addCleanup(self.logger.close)
        self.settings = dict(url='https://example.invalid/acess-event', key='chave-ficticia',
                             retry=10, poll=2, mapping={'catraca-01': 'CATRACA_01'})

    def registrar(self, sentido='entrada', quando=AGORA):
        with patch.object(a2.time, 'time', return_value=quando):
            return self.logger.register(CPF, sentido, 'imx519', 'catraca-01', ID, 7, UTC, {})

    def fila(self):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            return conn.execute('SELECT log_id, sent_at, attempts, last_error FROM cloud_access_outbox ORDER BY log_id').fetchall()

    def test_log_e_fila_persistente(self):
        ids = [self.registrar('entrada'), self.registrar('saida')]
        self.assertEqual([r[0] for r in self.fila()], ids)
        self.assertEqual(api.next_cloud_event()['log_id'], ids[0])
        # Novo acesso ao banco: fila deve continuar disponível.
        api.ensure_database()
        self.assertEqual(api.next_cloud_event()['log_id'], ids[0])

    def test_transacao_revertida_nao_cria_fila(self):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute('INSERT INTO access_logs(cpf,direction,occurred_at,source_id,turnstile_id) VALUES(?,?,?,?,?)',
                         (CPF, 'entrada', AGORA, 'imx519', 'catraca-01'))
            conn.rollback()
        self.assertEqual(self.fila(), [])

    def test_api_consulta_e_filtro(self):
        entrada = self.registrar('entrada')
        self.registrar('saida')
        resultado = api.get_access_logs(direction='entrada', limit=10, offset=0)
        self.assertEqual(resultado['total'], 1)
        self.assertEqual(resultado['data'][0]['id'], entrada)
        self.assertEqual(api.get_access_log(entrada)['frame_index'], 7)
        with self.assertRaises(HTTPException) as exc:
            api.get_access_log(99999)
        self.assertEqual(exc.exception.status_code, 404)

    def test_envio_http_payload_headers(self):
        self.registrar('saida')
        session = MagicMock()
        session.post.return_value.__enter__.return_value.status_code = 201
        self.assertIsNone(api.send_cloud_event(session, api.next_cloud_event(), self.settings))
        session.post.assert_called_once_with(self.settings['url'],
            json={'sentido': 'saida', 'cpf': int(CPF), 'catraca_id': 'CATRACA_01'},
            headers={'X-API-Key': 'chave-ficticia', 'Content-Type': 'application/json'},
            timeout=(3, 5), allow_redirects=False)

    def test_falha_e_reenvio_fifo(self):
        primeiro, segundo = self.registrar(), self.registrar('saida')
        session = MagicMock()
        session.post.return_value.__enter__.return_value.status_code = 503
        erro = api.send_cloud_event(session, api.next_cloud_event(), self.settings)
        self.assertEqual(erro, 'HTTP 503')
        api.update_cloud_event(primeiro, erro)
        self.assertEqual(self.fila()[0], (primeiro, None, 1, 'HTTP 503'))
        self.assertEqual(api.next_cloud_event()['log_id'], primeiro)
        session.post.return_value.__enter__.return_value.status_code = 200
        erro = api.send_cloud_event(session, api.next_cloud_event(), self.settings)
        self.assertIsNone(erro)
        api.update_cloud_event(primeiro, erro)
        self.assertIsNotNone(self.fila()[0][1])
        self.assertEqual(self.fila()[0][2], 2)
        self.assertEqual(api.next_cloud_event()['log_id'], segundo)
        api.update_cloud_event(segundo)
        self.assertIsNone(api.next_cloud_event())

    def test_worker_tenta_novamente_apos_falha(self):
        log_id = self.registrar()
        stop = Mock()
        stop.is_set.side_effect = [False, False, False, False, True]
        session = MagicMock()
        respostas = [MagicMock(status_code=503), MagicMock(status_code=200)]
        session.post.return_value.__enter__.side_effect = respostas
        with patch.object(api.requests, 'Session') as criar_session:
            criar_session.return_value.__enter__.return_value = session
            api.cloud_sync_worker(stop, self.settings)
        self.assertEqual(session.post.call_count, 2)
        stop.wait.assert_called_once_with(self.settings['retry'])
        registro = self.fila()[0]
        self.assertEqual(registro[0], log_id)
        self.assertIsNotNone(registro[1])
        self.assertEqual(registro[2], 2)
        self.assertIsNone(api.next_cloud_event())

    def test_timeout_http_nao_propaga(self):
        self.registrar()
        session = Mock()
        session.post.side_effect = requests.Timeout('simulado')
        self.assertEqual(api.send_cloud_event(session, api.next_cloud_event(), self.settings), 'Timeout')

    def test_status_sincronizacao(self):
        self.registrar()
        id2 = self.registrar('saida')
        api.update_cloud_event(id2)
        with patch.object(api, 'cloud_settings', return_value=(self.settings, None)):
            status = api.cloud_sync_status()
        self.assertEqual((status['pendentes'], status['enviados']), (1, 1))
        self.assertNotIn('cpf', str(status).lower())
        self.assertNotIn(self.settings['key'], str(status))

    def test_retencao_remove_log_e_fila(self):
        antigo = self.registrar(quando=AGORA-api.RETENTION_SECONDS-1)
        recente = self.registrar(quando=AGORA)
        with patch.object(api.time, 'time', return_value=AGORA):
            self.assertEqual(api.cleanup_old_logs(), 1)
        self.assertEqual([r[0] for r in self.fila()], [recente])
        with self.assertRaises(HTTPException):
            api.get_access_log(antigo)

    def test_dashboard_mascara_cpf(self):
        self.registrar()
        resposta = api.visualizar(periodo='tudo')
        texto = resposta.body.decode('utf-8')
        self.assertIn('123.***.***-09', texto)
        self.assertNotIn(CPF, texto)

    def test_configuracao_nuvem(self):
        with patch.dict('os.environ', {'A2_CLOUD_SYNC_ENABLED': 'true',
                       'A2_CLOUD_ACCESS_URL': 'https://example.invalid/acess-event',
                       'ACCESS_EVENT_KEY': 'teste', 'A2_CLOUD_RETRY_SECONDS': '10',
                       'A2_CLOUD_POLL_SECONDS': '2', 'A2_CLOUD_TURNSTILE_MAP': '{}'}):
            settings, erro = api.cloud_settings()
            self.assertIsNone(erro)
            self.assertEqual(settings['key'], 'teste')
            with patch.dict('os.environ', {'ACCESS_EVENT_KEY': ''}):
                self.assertIsNone(api.cloud_settings()[0])


if __name__ == '__main__':
    unittest.main()
