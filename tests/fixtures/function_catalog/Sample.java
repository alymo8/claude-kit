public class Sample {
    private int count = compute(1);

    public static int compute(int x) {
        if (x > 0) {
            return x;
        }
        return 0;
    }

    protected <T> java.util.List<T> wrapAll(T item) {
        return java.util.List.of(item);
    }

    private void _skipMe() {}
}
