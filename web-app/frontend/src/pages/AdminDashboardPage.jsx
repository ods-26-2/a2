import React, { useState, useEffect, useMemo, useCallback } from 'react';
import AdminSidebar from '../components/admin/AdminSidebar';
import AdminHeader from '../components/admin/AdminHeader';
import TableToolbar from '../components/admin/TableToolbar';
import UserTable from '../components/admin/UserTable';
import ApiConfigCard from '../components/admin/ApiConfigCard';
import AdminPasswordCard from '../components/admin/AdminPasswordCard';
import ApiKeysCard from '../components/admin/ApiKeysCard';
import ApiDocsCard from '../components/admin/ApiDocsCard';
import UserModal from '../components/UserModal';
import {
  fetchAdminUsers,
  fetchAdminConfig,
  createOrUpdateAdminUser,
  deleteAdminUser,
} from '../services/adminApi';
import { formatCpfDisplay, isDateExpired } from '../utils/formatters';

export default function AdminDashboardPage({ onNavigateToApp, adminUser, onLogout }) {
  const [activeTab, setActiveTab] = useState('users');
  const [users, setUsers] = useState([]);

  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedUserToConfigure, setSelectedUserToConfigure] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [usersData, configData] = await Promise.all([
        fetchAdminUsers().catch((err) => {
          if (err.message.includes('Sessão expirada') && onLogout) onLogout();
          return [];
        }),
        fetchAdminConfig().catch(() => null),
      ]);
      setUsers(Array.isArray(usersData) ? usersData : []);
      setConfig(configData);
    } catch (err) {
      console.error('Erro ao carregar dados do admin:', err);
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleDeleteUser = async (cpf) => {
    if (!window.confirm(`Deseja remover o acesso do CPF ${formatCpfDisplay(cpf)}?`)) {
      return;
    }
    try {
      await deleteAdminUser(cpf);
      setUsers((prev) => prev.filter((u) => u.cpf !== cpf));
      loadData();
    } catch (err) {
      alert(err.message || 'Erro ao excluir usuário');
    }
  };

  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      const cleanSearch = searchTerm.replace(/\D/g, '');
      const strCpf = String(u.cpf || '');
      const matchesSearch = cleanSearch ? strCpf.includes(cleanSearch) : true;
      if (!matchesSearch) return false;

      if (statusFilter === 'recurring') return u.is_recurring;
      if (statusFilter === 'specific') return !u.is_recurring;
      if (statusFilter === 'expired') {
        return u.expiration_date ? isDateExpired(u.expiration_date) : false;
      }
      if (statusFilter === 'valid') {
        return u.expiration_date ? !isDateExpired(u.expiration_date) : true;
      }
      return true;
    });
  }, [users, searchTerm, statusFilter]);

  return (
    <div className="w-full h-full flex bg-[#F8FAFC] text-[#0F172A] overflow-hidden">
      <AdminSidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onNavigateToApp={onNavigateToApp}
        onLogout={onLogout}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <AdminHeader activeTab={activeTab} />

        <main className="flex-1 overflow-y-auto p-6 sm:p-8">
          <div className="max-w-[1400px] mx-auto space-y-6">
            {activeTab === 'users' ? (
              <>
                <TableToolbar
                  searchTerm={searchTerm}
                  onSearchChange={setSearchTerm}
                  statusFilter={statusFilter}
                  onFilterChange={setStatusFilter}
                  onOpenNewUser={() => {
                    setSelectedUserToConfigure(null);
                    setIsModalOpen(true);
                  }}
                />

                <UserTable
                  users={filteredUsers}
                  onDeleteUser={handleDeleteUser}
                  onEditExpiration={(user) => {
                    setSelectedUserToConfigure(user);
                    setIsModalOpen(true);
                  }}
                />
              </>
            ) : (
              <div className="space-y-6">
                <ApiConfigCard
                  initialBatchSize={config?.payload_batch_size}
                  onConfigUpdated={loadData}
                />
                <ApiKeysCard />
                <ApiDocsCard />
                <AdminPasswordCard />
              </div>
            )}
          </div>
        </main>
      </div>

      {isModalOpen && (
        <UserModal
          initialUser={selectedUserToConfigure}
          onClose={() => {
            setIsModalOpen(false);
            setSelectedUserToConfigure(null);
          }}
          onSaved={async (userData) => {
            await createOrUpdateAdminUser(userData);
            loadData();
          }}
        />
      )}
    </div>
  );
}
