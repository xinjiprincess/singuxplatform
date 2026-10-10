import {
  ActionItem,
  TableActions,
  XProTable,
} from '@/components/ProComponents';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { SUCCESS_CODE } from '@/constants/codes.constants';
import { dict } from '@/services/i18nRuntime';
import {
  apiDeleteSystemUser,
  apiDisableSystemUser,
  apiEnableSystemUser,
  apiSystemUserList,
} from '@/services/systemManage';
import { getPlatformCapabilities } from '@/services/tenantPolicy';
import { setUsersBatchStatus, type BatchResult } from '@/services/userBatch';
import { getUsersForExport } from '@/services/userExport';
import styles from '@/styles/systemManage.less';
import { UserRoleEnum, UserStatusEnum } from '@/types/enums/systemManage';
import type { SystemUserListInfo } from '@/types/interfaces/systemManage';
import { getIntegerOnlyFieldProps } from '@/utils/inputValidation';
import { downloadBatchJson } from '@/utils/userBatch';
import { usersToCsv } from '@/utils/userExport';
import { DownloadOutlined, PlusOutlined } from '@ant-design/icons';
import type {
  ActionType,
  FormInstance,
  ProColumns,
} from '@ant-design/pro-components';
import { Button, Modal, message } from 'antd';
import classNames from 'classnames';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useModel } from 'umi';
import BatchUsersModal from './components/BatchUsersModal';
import DataPermissionModal from './components/DataPermissionModal';
import ResetPasswordModal from './components/ResetPasswordModal';
import UserAuthModal from './components/UserAuthModal';
import UserFormModal from './components/UserFormModal';
import UserViewMenuModal from './components/UserViewMenuModal';
import MessageSendModal from './MessageSendModal';

const cx = classNames.bind(styles);

/**
 * 用户管理
 */
const UserManage: React.FC = () => {
  const { hasPermissionByMenuCode } = useModel('menuModel');

  const actionRef = useRef<ActionType>();
  const formRef = useRef<FormInstance>();
  const [exporting, setExporting] = useState(false);
  const [batchOpen, setBatchOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<React.Key[]>([]);
  const [batchBusy, setBatchBusy] = useState(false);
  const [canBatchStatus, setCanBatchStatus] = useState(false);
  useEffect(() => {
    let active = true;
    getPlatformCapabilities()
      .then((caps) => {
        if (active)
          setCanBatchStatus(!caps.membershipEnabled || caps.platformAdmin);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);
  const runBatchStatus = (enabled: boolean) =>
    Modal.confirm({
      title: dict(
        enabled ? 'PC.Pages.UserBatch.enable' : 'PC.Pages.UserBatch.disable',
      ),
      content: `${dict('PC.Pages.UserBatch.selected')}: ${selectedIds.length}`,
      onOk: async () => {
        setBatchBusy(true);
        try {
          const results = await setUsersBatchStatus(
            selectedIds.map(Number),
            enabled,
          );
          const failed = results.filter((row: BatchResult) => !row.success);
          setSelectedIds(
            failed.flatMap((row) => (row.id === null ? [] : [row.id])),
          );
          actionRef.current?.reload();
          if (failed.length) {
            downloadBatchJson(failed, 'singux-user-failures.json');
            message.warning(dict('PC.Pages.UserBatch.partialFailure'));
          } else message.success(dict('PC.Pages.UserBatch.success'));
        } catch {
          message.error(dict('PC.Pages.UserBatch.failed'));
        } finally {
          setBatchBusy(false);
        }
      },
    });
  const exportFilter = useRef<{
    id?: number;
    role?: string;
    userName?: string;
  }>({});
  const handleExport = async () => {
    setExporting(true);
    try {
      const users = await getUsersForExport({ ...exportFilter.current });
      // 表头顺序必须与 usersToCsv 读取的字段顺序一致。
      // 这里逐条写全 key 而不是拼 `PC.Pages.UserManage.Index.${key}`：
      // 拼接出来的 key 会躲过 scripts/check-hardcoded-i18n.js 的静态检查，
      // 写错了只能等导出时才在控制台看到 Missing translation entry。
      const headers = [
        dict('PC.Pages.UserManage.Index.userId'),
        dict('PC.Pages.UserManage.Index.userName'),
        dict('PC.Pages.UserManage.Index.nickName'),
        dict('PC.Pages.UserManage.Index.email'),
        dict('PC.Pages.UserManage.Index.phoneNumber'),
        dict('PC.Pages.UserManage.Index.type'),
        dict('PC.Pages.UserManage.Index.status'),
        dict('PC.Pages.UserManage.Index.joinTime'),
      ];
      const url = URL.createObjectURL(
        new Blob([usersToCsv(users, headers)], {
          type: 'text/csv;charset=utf-8',
        }),
      );
      const link = document.createElement('a');
      link.href = url;
      link.download = `users-${new Date()
        .toISOString()
        .replace(/[:.]/g, '-')}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      message.error(dict('PC.Pages.UserManage.exportFailed'));
    } finally {
      setExporting(false);
    }
  };
  const location = useLocation();
  const [currentUserInfo, setCurrentUserInfo] =
    useState<SystemUserListInfo | null>(null);

  // 状态弹窗控制
  const [messageSendOpen, setMessageSendOpen] = useState(false);
  const [openAuthModal, setOpenAuthModal] = useState(false);
  const [openViewMenuModal, setOpenViewMenuModal] = useState(false);
  const [openDataPermissionModal, setOpenDataPermissionModal] = useState(false);
  const [openUserFormModal, setOpenUserFormModal] = useState(false);
  const [openResetPasswordModal, setOpenResetPasswordModal] = useState(false);
  const [isEdit, setIsEdit] = useState(false);

  // 操作处理函数
  const handleAddUser = useCallback(() => {
    setIsEdit(false);
    setCurrentUserInfo(null);
    setOpenUserFormModal(true);
  }, []);

  const handleEditUser = useCallback((record: SystemUserListInfo) => {
    setIsEdit(true);
    setCurrentUserInfo(record);
    setOpenUserFormModal(true);
  }, []);

  const handleResetPassword = useCallback((record: SystemUserListInfo) => {
    setCurrentUserInfo(record);
    setOpenResetPasswordModal(true);
  }, []);

  const handleAuth = useCallback((userInfo: SystemUserListInfo) => {
    setCurrentUserInfo(userInfo);
    setOpenAuthModal(true);
  }, []);

  const handleViewMenu = useCallback((userInfo: SystemUserListInfo) => {
    setCurrentUserInfo(userInfo);
    setOpenViewMenuModal(true);
  }, []);

  const handleViewDataPermission = useCallback(
    (userInfo: SystemUserListInfo) => {
      setCurrentUserInfo(userInfo);
      setOpenDataPermissionModal(true);
    },
    [],
  );

  const handleEnable = useCallback(async (record: SystemUserListInfo) => {
    const res = await apiEnableSystemUser({ id: record.id });
    if (res.code === SUCCESS_CODE) {
      message.success(dict('PC.Pages.UserManage.Index.enableSuccess'));
      actionRef.current?.reload();
    }
  }, []);

  const handleDisable = useCallback(async (record: SystemUserListInfo) => {
    const res = await apiDisableSystemUser({ id: record.id });
    if (res.code === SUCCESS_CODE) {
      message.success(dict('PC.Pages.UserManage.Index.disableSuccess'));
      actionRef.current?.reload();
    }
  }, []);

  const handleDelete = useCallback(async (record: SystemUserListInfo) => {
    const res = await apiDeleteSystemUser({ id: record.id });
    if (res.code === SUCCESS_CODE) {
      message.success(dict('PC.Pages.UserManage.Index.deleteSuccess'));
      actionRef.current?.reload();
    }
  }, []);

  const handleSuccess = useCallback(() => {
    setOpenUserFormModal(false);
    actionRef.current?.reload();
  }, []);

  const handleReset = useCallback(() => {
    // 重置表单
    formRef.current?.resetFields();
    // 重置表格状态
    actionRef.current?.reset?.();
    // 设置分页参数:第1页,每页15条
    actionRef.current?.setPageInfo?.({ current: 1, pageSize: 15 });
    // 延迟一下再重新加载,确保分页参数已设置
    actionRef.current?.reload();
  }, []);

  // 监听 location.state 变化
  // 当 state 中存在 _t 变量时，说明是通过菜单切换过来的，需要清空 query 参数
  useEffect(() => {
    const state = location.state as any;
    if (state?._t) {
      handleReset();
    }
  }, [location.state, handleReset]);

  // 操作列配置
  const getActions = useCallback(
    (record: SystemUserListInfo): ActionItem<SystemUserListInfo>[] => {
      return [
        {
          key: 'resetPassword',
          label: dict('PC.Pages.UserManage.Index.resetPassword'),
          disabled: !hasPermissionByMenuCode(
            'user_manage',
            'user_manage_modify',
          ),
          onClick: handleResetPassword,
        },
        {
          key: 'disable',
          label: dict('PC.Pages.UserManage.Index.disable'),
          visible: record.status === UserStatusEnum.Enabled,
          disabled: !hasPermissionByMenuCode(
            'user_manage',
            'user_manage_disable',
          ),
          onClick: handleDisable,
        },
        {
          key: 'enable',
          label: dict('PC.Pages.UserManage.Index.enable'),
          visible: record.status !== UserStatusEnum.Enabled,
          disabled: !hasPermissionByMenuCode(
            'user_manage',
            'user_manage_enable',
          ),
          onClick: handleEnable,
        },
        {
          key: 'delete',
          label: dict('PC.Pages.UserManage.Index.delete'),
          danger: true,
          confirm: {},
          disabled: !hasPermissionByMenuCode(
            'user_manage',
            'user_manage_disable',
          ),
          onClick: handleDelete,
        },
        {
          key: 'auth',
          label: dict('PC.Pages.UserManage.Index.auth'),
          disabled:
            !hasPermissionByMenuCode('user_manage', 'user_manage_bind_role') &&
            !hasPermissionByMenuCode('user_manage', 'user_manage_bind_group'),
          onClick: handleAuth,
        },
        {
          key: 'edit',
          label: dict('PC.Pages.UserManage.Index.edit'),
          disabled: !hasPermissionByMenuCode(
            'user_manage',
            'user_manage_modify',
          ),
          onClick: handleEditUser,
        },
        {
          key: 'viewMenu',
          label: dict('PC.Pages.UserManage.Index.viewMenuResourcePermission'),
          disabled: !hasPermissionByMenuCode(
            'user_manage',
            'user_manage_query_menu_permission',
          ),
          onClick: handleViewMenu,
        },
        {
          key: 'dataPermission',
          label: dict('PC.Pages.UserManage.Index.viewDataPermission'),
          disabled: !hasPermissionByMenuCode(
            'user_manage',
            'user_manage_query_data_permission',
          ),
          onClick: handleViewDataPermission,
        },
      ];
    },
    [
      hasPermissionByMenuCode,
      handleEditUser,
      handleResetPassword,
      handleEnable,
      handleDisable,
      handleDelete,
      handleAuth,
      handleViewMenu,
      handleViewDataPermission,
    ],
  );

  const columns: ProColumns<SystemUserListInfo>[] = [
    {
      title: dict('PC.Pages.UserManage.Index.userId'),
      dataIndex: 'id',
      width: 140,
      fieldProps: getIntegerOnlyFieldProps(
        dict('PC.Pages.UserManage.Index.placeholderUserId'),
      ),
    },
    {
      title: dict('PC.Pages.UserManage.Index.userName'),
      dataIndex: 'userName',
      width: 160,
      fieldProps: {
        placeholder: dict('PC.Pages.UserManage.Index.userFullName'),
      },
    },
    {
      title: dict('PC.Pages.UserManage.Index.nickName'),
      dataIndex: 'nickName',
      width: 100,
      hideInSearch: true,
    },
    {
      title: dict('PC.Pages.UserManage.Index.phoneNumber'),
      dataIndex: 'phone',
      width: 140,
      hideInSearch: true,
    },
    {
      title: dict('PC.Pages.UserManage.Index.email'),
      dataIndex: 'email',
      width: 200,
      hideInSearch: true,
    },
    {
      title: dict('PC.Pages.UserManage.Index.type'),
      dataIndex: 'role',
      width: 100,
      valueType: 'select',
      valueEnum: {
        [UserRoleEnum.Admin]: {
          text: dict('PC.Pages.UserManage.Index.admin'),
        },
        [UserRoleEnum.User]: {
          text: dict('PC.Pages.UserManage.Index.member'),
        },
      },
    },
    {
      title: dict('PC.Pages.UserManage.Index.status'),
      dataIndex: 'status',
      width: 90,
      hideInSearch: true,
      render: (_, record: SystemUserListInfo) => {
        const isEnabled = record.status === UserStatusEnum.Enabled;
        return (
          <span>
            <span
              className={cx(
                styles['dot-circle'],
                isEnabled ? styles['dot-green'] : styles['dot-red'],
              )}
            ></span>
            {isEnabled
              ? dict('PC.Pages.UserManage.Index.normal')
              : dict('PC.Pages.UserManage.Index.disabled')}
          </span>
        );
      },
    },
    {
      title: dict('PC.Pages.UserManage.Index.joinTime'),
      dataIndex: 'created',
      width: 180,
      hideInSearch: true,
      valueType: 'dateTime',
    },
    {
      title: dict('PC.Pages.UserManage.Index.action'),
      valueType: 'option',
      fixed: 'right',
      align: 'center',
      width: 220,
      render: (_, record) => (
        <TableActions<SystemUserListInfo>
          record={record}
          actions={getActions(record)}
        />
      ),
    },
  ];

  const request = async (params: {
    pageSize?: number;
    current?: number;
    id?: string;
    userName?: string;
    role?: string;
  }) => {
    const response = await apiSystemUserList({
      pageNo: params.current || 1,
      pageSize: params.pageSize || 15,
      queryFilter: {
        id: params.id ? Number(params.id) : undefined,
        role: params.role || undefined,
        userName: params.userName,
      },
    });

    if (response.code === SUCCESS_CODE) {
      exportFilter.current = {
        id: params.id ? Number(params.id) : undefined,
        role: params.role || undefined,
        userName: params.userName,
      };
    }
    return {
      data: response.data.records,
      total: response.data.total,
      success: response.code === SUCCESS_CODE,
    };
  };

  return (
    <WorkspaceLayout
      title={dict('PC.Pages.UserManage.Index.userManage')}
      hideScroll
      rightSlot={[
        hasPermissionByMenuCode('user_manage', 'user_manage_add') && (
          <Button
            key="batchAdd"
            icon={<PlusOutlined />}
            onClick={() => setBatchOpen(true)}
          >
            {dict('PC.Pages.UserBatch.add')}
          </Button>
        ),
        hasPermissionByMenuCode('user_manage', 'user_manage_query') && (
          <Button
            key="export"
            icon={<DownloadOutlined />}
            loading={exporting}
            onClick={handleExport}
          >
            {dict('PC.Pages.UserManage.exportCsv')}
          </Button>
        ),
        hasPermissionByMenuCode('user_manage', 'user_manage_add') && (
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAddUser}
          >
            {dict('PC.Pages.UserManage.Index.addUser')}
          </Button>
        ),
        hasPermissionByMenuCode('user_manage', 'user_manage_send_message') && (
          <Button
            key="message"
            type="primary"
            onClick={() => setMessageSendOpen(true)}
          >
            {dict('PC.Pages.UserManage.Index.sendMessage')}
          </Button>
        ),
      ]}
    >
      <XProTable<SystemUserListInfo>
        actionRef={actionRef}
        formRef={formRef}
        rowKey="id"
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
          pageSizeOptions: [20, 50, 100, 200],
        }}
        rowSelection={{
          selectedRowKeys: selectedIds,
          preserveSelectedRowKeys: true,
          onChange: (keys) => setSelectedIds(keys),
          getCheckboxProps: (record) => ({
            disabled: batchBusy || record.role === UserRoleEnum.Admin,
          }),
        }}
        toolBarRender={() =>
          !canBatchStatus
            ? []
            : [
                hasPermissionByMenuCode(
                  'user_manage',
                  'user_manage_disable',
                ) && (
                  <Button
                    key="disableBatch"
                    danger
                    disabled={
                      !selectedIds.length ||
                      selectedIds.length > 200 ||
                      batchBusy
                    }
                    onClick={() => runBatchStatus(false)}
                  >
                    {dict('PC.Pages.UserBatch.disable')}
                  </Button>
                ),
                hasPermissionByMenuCode(
                  'user_manage',
                  'user_manage_enable',
                ) && (
                  <Button
                    key="enableBatch"
                    disabled={
                      !selectedIds.length ||
                      selectedIds.length > 200 ||
                      batchBusy
                    }
                    onClick={() => runBatchStatus(true)}
                  >
                    {dict('PC.Pages.UserBatch.enable')}
                  </Button>
                ),
              ]
        }
        columns={columns}
        request={request}
        onReset={handleReset}
        showQueryButtons={hasPermissionByMenuCode(
          'user_manage',
          'user_manage_query',
        )}
      />

      {batchOpen && (
        <BatchUsersModal
          onClose={() => setBatchOpen(false)}
          onChanged={() => actionRef.current?.reload()}
        />
      )}

      {/* 用户新增/编辑弹窗 */}
      <UserFormModal
        open={openUserFormModal}
        isEdit={isEdit}
        record={currentUserInfo}
        onCancel={() => setOpenUserFormModal(false)}
        onSuccess={handleSuccess}
      />
      <MessageSendModal
        open={messageSendOpen}
        onCancel={() => setMessageSendOpen(false)}
      />

      {/* 用户授权弹窗（包含角色和用户组） */}
      <UserAuthModal
        open={openAuthModal}
        targetId={currentUserInfo?.id || 0}
        userName={currentUserInfo?.userName || currentUserInfo?.nickName}
        role={currentUserInfo?.role}
        onCancel={() => setOpenAuthModal(false)}
      />
      <UserViewMenuModal
        open={openViewMenuModal}
        userId={currentUserInfo?.id || 0}
        onCancel={() => setOpenViewMenuModal(false)}
      />
      <DataPermissionModal
        open={openDataPermissionModal}
        userId={currentUserInfo?.id || 0}
        userName={currentUserInfo?.userName || currentUserInfo?.nickName}
        onCancel={() => setOpenDataPermissionModal(false)}
      />
      <ResetPasswordModal
        open={openResetPasswordModal}
        record={currentUserInfo}
        onCancel={() => setOpenResetPasswordModal(false)}
        onSuccess={() => {
          setOpenResetPasswordModal(false);
        }}
      />
    </WorkspaceLayout>
  );
};

export default UserManage;
