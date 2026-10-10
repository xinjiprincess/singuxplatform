public class McpLoggingTestRunner {
    public static void main(String[] args) throws Exception {
        int count = 0;
        for (String name : args) {
            Class<?> type = Class.forName(name);
            var constructor = type.getDeclaredConstructor();
            constructor.setAccessible(true);
            for (var method : type.getDeclaredMethods()) {
                if (method.getAnnotation(org.junit.jupiter.api.Test.class) == null) continue;
                method.setAccessible(true);
                try {
                    method.invoke(constructor.newInstance());
                } catch (java.lang.reflect.InvocationTargetException error) {
                    throw new AssertionError(name + "." + method.getName(), error.getCause());
                }
                System.out.println("PASS " + type.getSimpleName() + "." + method.getName());
                count++;
            }
        }
        System.out.println("MCP_LOG_TESTS_OK count=" + count);
    }
}
