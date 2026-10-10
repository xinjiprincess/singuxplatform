import com.xspaceagi.knowledge.domain.service.impl.KnowledgeDocumentDomainService;
import com.xspaceagi.knowledge.domain.repository.IKnowledgeConfigRepository;
import com.xspaceagi.knowledge.domain.model.KnowledgeConfigModel;
import com.xspaceagi.agent.core.adapter.application.ModelApplicationService;
import com.xspaceagi.system.application.service.TenantConfigApplicationService;
import com.xspaceagi.system.application.dto.TenantConfigDto;
import com.xspaceagi.system.spec.common.UserContext;
import org.springframework.core.ParameterizedTypeReference;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

public class KnowledgeModelSelectionSmoke {
    static void inject(Object object, String name, Object value) throws Exception {
        var field = object.getClass().getDeclaredField(name);
        field.setAccessible(true); field.set(object, value);
    }
    public static void main(String[] args) throws Exception {
        var service = new KnowledgeDocumentDomainService();
        var repository = mock(IKnowledgeConfigRepository.class);
        var models = mock(ModelApplicationService.class);
        var tenants = mock(TenantConfigApplicationService.class);
        inject(service, "knowledgeConfigRepository", repository);
        inject(service, "modelApplicationService", models);
        inject(service, "tenantConfigApplicationService", tenants);
        var config = new KnowledgeConfigModel(); config.setId(7L); config.setTenantId(1L); config.setChatModelId(26L);
        when(repository.queryOneInfoById(7L)).thenReturn(config);
        var context = UserContext.builder().tenantId(1L).userId(1L).build();
        var method = service.getClass().getDeclaredMethod("processQa", Long.class, String.class, Long.class, Long.class, Long.class, UserContext.class);
        method.setAccessible(true);
        method.invoke(service, 1L, "test", 2L, 7L, 3L, context);
        verify(models).call(eq(26L), anyString(), eq("test"), any(ParameterizedTypeReference.class));
        verifyNoInteractions(tenants);
        System.out.println("PASS: explicit knowledge model wins over tenant default");
        clearInvocations(models);
        config.setChatModelId(null);
        var tenant = new TenantConfigDto(); tenant.setDefaultKnowledgeModelId(40L);
        when(tenants.getTenantConfig(1L)).thenReturn(tenant);
        method.invoke(service, 1L, "test", 2L, 7L, 3L, context);
        verify(models).call(eq(40L), anyString(), eq("test"), any(ParameterizedTypeReference.class));
        System.out.println("PASS: asynchronous call uses supplied tenant context");
        clearInvocations(models);
        tenant.setDefaultKnowledgeModelId(null);
        try { method.invoke(service, 1L, "test", 2L, 7L, 3L, context); throw new AssertionError("Missing model accepted"); }
        catch (java.lang.reflect.InvocationTargetException e) {
            if (!(e.getCause() instanceof IllegalStateException)) throw e;
        }
        verifyNoInteractions(models);
        System.out.println("PASS: missing model fails before network call");
        config.setTenantId(2L);
        try { method.invoke(service, 1L, "test", 2L, 7L, 3L, context); throw new AssertionError("Cross-tenant knowledge accepted"); }
        catch (java.lang.reflect.InvocationTargetException expected) {
            if (!(expected.getCause() instanceof com.xspaceagi.system.spec.exception.KnowledgeException)) throw expected;
        }
        verifyNoInteractions(models);
        System.out.println("PASS: cross-tenant knowledge cannot reach model");
    }
}
