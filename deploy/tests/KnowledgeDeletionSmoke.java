import com.xspaceagi.search.infra.elasticsearch.ElasticsearchServiceImpl;
import com.xspaceagi.knowledge.core.infra.rpc.SearchRpcService;
import com.xspaceagi.knowledge.core.application.service.impl.KnowledgeFullTextSearchClientImpl;
import com.xspaceagi.knowledge.domain.service.impl.KnowledgeFullTextSearchDomainServiceImpl;
import org.elasticsearch.client.RestClient;
import org.elasticsearch.client.Request;
import org.apache.http.HttpHost;
import org.apache.http.util.EntityUtils;

public class KnowledgeDeletionSmoke {
    static void inject(Object target, String fieldName, Object value) throws Exception {
        var field = target.getClass().getDeclaredField(fieldName); field.setAccessible(true); field.set(target, value);
    }
    static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message); System.out.println("PASS: " + message);
    }
    static String request(RestClient client, String method, String path, String json) throws Exception {
        var request = new Request(method, path); if (json != null) request.setJsonEntity(json);
        var response = client.performRequest(request); return EntityUtils.toString(response.getEntity());
    }
    public static void main(String[] args) throws Exception {
        String url = "http://elasticsearch:9200";
        try (var client = RestClient.builder(HttpHost.create(url)).build()) {
            var info = request(client, "GET", "/", null);
            check(info.contains("8.18.0"), "real Elasticsearch server is 8.18.0");
            var search = new ElasticsearchServiceImpl(); inject(search, "esUrl", url);
            var init = search.getClass().getDeclaredMethod("init"); init.setAccessible(true); init.invoke(search);
            try {
                var rpc = new SearchRpcService(); inject(rpc, "iSearchRpcService", search);
                var adapter = new KnowledgeFullTextSearchClientImpl(); inject(adapter, "searchRpcService", rpc);
                var domain = new KnowledgeFullTextSearchDomainServiceImpl(); inject(domain, "fullTextSearchClient", adapter); inject(domain, "fullTextSearchDomainService", domain);
                check(domain.deleteByKbId(7L, 1L) == 0L, "missing knowledge index can be deleted");
                check("[]".equals(request(client, "GET", "/_cat/indices?format=json", null).trim()), "delete does not create missing index or require IK");
                var create = search.getClass().getDeclaredMethod("createIndexIfNotExists", Class.class);
                create.setAccessible(true);
                create.invoke(search, com.xspaceagi.knowledge.core.infra.rpc.vo.KnowledgeSearchDocument.class);
                check(request(client, "GET", "/knowledge/_mapping", null).contains("standard"), "new full-text index uses built-in analyzer without IK");
                var segment = com.xspaceagi.knowledge.core.infra.rpc.vo.KnowledgeSearchDocument.builder()
                        .id("smoke-write").tenantId(1L).kbId(7L).docId(1L).rawText("\u6821\u56ed\u65b0\u751f\u52a9\u624b").build();
                search.bulkIndex(java.util.List.of(segment));
                request(client, "POST", "/knowledge/_refresh", null);
                check(request(client, "GET", "/knowledge/_doc/smoke-write", null).contains("\"found\":true"), "real full-text bulk write succeeds without IK");
                check(request(client, "POST", "/knowledge/_search", "{\"query\":{\"match\":{\"rawText\":\"\\u6821\\u56ed\"}}}").contains("smoke-write"), "Chinese document can be retrieved using built-in analyzer");
                request(client, "DELETE", "/knowledge", null);
                request(client, "PUT", "/knowledge", "{\"mappings\":{\"properties\":{\"tenantId\":{\"type\":\"long\"},\"kbId\":{\"type\":\"long\"},\"docId\":{\"type\":\"long\"},\"id\":{\"type\":\"keyword\"},\"rawText\":{\"type\":\"text\"}}}}");
                request(client, "PUT", "/knowledge/_doc/1001?refresh=true", "{\"id\":\"1001\",\"tenantId\":1,\"kbId\":7,\"docId\":1,\"rawText\":\"delete me\"}");
                request(client, "PUT", "/knowledge/_doc/1002?refresh=true", "{\"id\":\"1002\",\"tenantId\":1,\"kbId\":8,\"docId\":2,\"rawText\":\"other KB\"}");
                request(client, "PUT", "/knowledge/_doc/1003?refresh=true", "{\"id\":\"1003\",\"tenantId\":2,\"kbId\":7,\"docId\":3,\"rawText\":\"other tenant\"}");
                check(domain.deleteByKbId(7L, 1L) == 1L, "configured KB segment deleted through real application client");
                request(client, "POST", "/knowledge/_refresh", null);
                check(request(client, "GET", "/knowledge/_count", null).contains("\"count\":2"), "other KB and tenant data preserved");
                check(request(client, "GET", "/knowledge/_doc/1002", null).contains("\"found\":true"), "other knowledge base preserved");
                check(request(client, "GET", "/knowledge/_doc/1003", null).contains("\"found\":true"), "other tenant preserved");
                check(domain.deleteByKbId(7L, 1L) == 0L, "repeated deletion succeeds");
                search.deleteDocument(com.xspaceagi.knowledge.core.infra.rpc.vo.KnowledgeSearchDocument.class, "1001");
                System.out.println("PASS: repeated document deletion succeeds");
            } finally {
                var destroy = search.getClass().getDeclaredMethod("destroy"); destroy.setAccessible(true); destroy.invoke(search);
            }
        }
    }
}
