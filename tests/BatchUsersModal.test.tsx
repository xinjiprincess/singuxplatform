import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
const api = vi.hoisted(() => ({ create: vi.fn() }));
vi.mock('@/services/userBatch', () => ({ createUsersBatch: api.create }));
vi.mock('@/services/i18nRuntime', () => ({ dict: (key: string) => key.split('.').pop() }));
import BatchUsersModal from '../src/pages/UserManage/components/BatchUsersModal';
afterEach(() => { cleanup(); vi.clearAllMocks(); });
describe('batch user retry surface', () => {
  it('removes successful inputs and retains failed rows without exporting passwords', async () => {
    const changed = vi.fn();
    api.create.mockResolvedValue([
      { row: 1, id: 1, userName: 'a', success: true, code: '0000', message: 'Created' },
      { row: 2, id: null, userName: 'b', success: false, code: 'INVALID_EMAIL', message: 'Invalid email' },
    ]);
    render(<BatchUsersModal onClose={vi.fn()} onChanged={changed} />);
    fireEvent.click(screen.getByRole('button', { name: /addRow/ }));
    fireEvent.change(screen.getAllByLabelText('userName')[0], { target: { value: 'a' } });
    fireEvent.change(screen.getAllByLabelText('userName')[1], { target: { value: 'b' } });
    fireEvent.change(screen.getAllByLabelText('password')[0], { target: { value: 'secret123' } });
    fireEvent.click(screen.getByRole('button', { name: 'importAll' }));
    await waitFor(() => expect(changed).toHaveBeenCalledOnce(), { timeout: 15000 });
    await waitFor(() => expect(screen.getAllByLabelText('userName')).toHaveLength(1), { timeout: 15000 });
    expect((screen.getByLabelText('userName') as HTMLInputElement).value).toBe('b');
    expect(screen.queryByDisplayValue('secret123')).toBeNull();
    expect(screen.getByText('Invalid email')).toBeTruthy();
  }, 30000);
});
