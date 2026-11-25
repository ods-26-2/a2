import React from 'react';
import { getAdminSession } from '../../services/adminApi';

export default function ApiDocsCard() {
  const session = getAdminSession();
  const href = session?.token ? `/admin/docs?token=${encodeURIComponent(session.token)}` : null;

  return (
    <div className='text-[13px]'>
      {href ? (
        <a
          href={href}
          target='_blank'
          rel='noreferrer'
          className='text-[#2563EB] hover:underline font-medium'
        >
          Ver documentacao
        </a>
      ) : (
        <span className='text-[#9CA3AF]'>Ver documentacao</span>
      )}
    </div>
  );
}
