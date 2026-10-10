import com.xspaceagi.mcp.application.service.McpDeployTaskServiceImpl;
import com.xspaceagi.mcp.adapter.domain.McpConfigDomainService;
import com.xspaceagi.mcp.infra.rpc.McpDeployRpcService;
import com.xspaceagi.mcp.infra.rpc.dto.McpDeployStatusResponse;
import com.xspaceagi.mcp.infra.rpc.enums.McpDeployStatusEnum;
import com.xspaceagi.mcp.sdk.enums.DeployStatusEnum;
import com.xspaceagi.system.application.dto.UserDto;
import com.xspaceagi.system.application.service.UserApplicationService;
import com.xspaceagi.system.application.service.NotifyMessageApplicationService;
import com.xspaceagi.system.sdk.service.dto.ScheduleTaskDto;
import java.util.Map;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

public class McpDeploymentSmoke {
    static void inject(Object target, String name, Object value) throws Exception {
        var field = target.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(target, value);
    }
    public static void main(String[] args) throws Exception {
        var service = new McpDeployTaskServiceImpl();
        var rpc = mock(McpDeployRpcService.class);
        var configs = mock(McpConfigDomainService.class);
        var users = mock(UserApplicationService.class);
        var notices = mock(NotifyMessageApplicationService.class);
        inject(service, "mcpDeployRpcService", rpc);
        inject(service, "mcpConfigDomainService", configs);
        inject(service, "userApplicationService", users);
        inject(service, "notifyMessageApplicationService", notices);
        var user = new UserDto(); user.setId(2L);
        when(users.queryById(2L)).thenReturn(user);
        var task = ScheduleTaskDto.builder().taskId("mcp:1:smoke").execTimes(0L).maxExecTimes(60L)
            .params(Map.of("id", 1L, "tenantId", 3L, "userId", 2L, "mcpConfig", "{}", "name", "Test", "installType", "NPX")).build();
        when(rpc.deploy(anyString(), anyString(), any())).thenThrow(new IllegalStateException("Connection refused"));
        if (!service.execute1(task)) throw new AssertionError("Proxy failure did not end task");
        verify(configs).update(argThat(value -> value.getId().equals(1L) && value.getDeployStatus() == DeployStatusEnum.DeployFailed));
        System.out.println("PASS: refused proxy ends task and marks failure");
        clearInvocations(configs, rpc);
        when(users.queryById(2L)).thenReturn(null);
        if (!service.execute1(task)) throw new AssertionError("Missing creator did not end task");
        verifyNoInteractions(rpc);
        verify(configs).update(argThat(value -> value.getDeployStatus() == DeployStatusEnum.DeployFailed));
        System.out.println("PASS: missing creator ends task and marks failure");
        when(users.queryById(2L)).thenReturn(user);
        reset(rpc); clearInvocations(configs);
        var pending = new McpDeployStatusResponse(); pending.setStatus(McpDeployStatusEnum.Pending);
        when(rpc.deploy(anyString(), anyString(), any())).thenReturn(pending);
        if (service.execute1(task)) throw new AssertionError("Pending task completed early");
        verifyNoInteractions(configs);
        System.out.println("PASS: pending deployment can continue polling");
        task.setExecTimes(59L);
        service.execute1(task);
        verify(configs).update(argThat(value -> value.getDeployStatus() == DeployStatusEnum.DeployFailed));
        System.out.println("PASS: final pending attempt marks timeout failure");
    }
}
