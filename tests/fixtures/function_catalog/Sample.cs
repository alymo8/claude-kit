namespace Fixture
{
    public class Sample
    {
        internal static string FormatLabel(string text)
        {
            if (text == null) return "";
            return text.Trim();
        }

        public async Task<int> CountAsync() => await Task.FromResult(1);

        private readonly Func<int> factory = () => 1;
    }
}
