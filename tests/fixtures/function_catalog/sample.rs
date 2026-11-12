pub fn parse_args(input: &str) -> String {
    input.to_string()
}

pub(crate) async fn fetch_remote(url: &str) -> String {
    url.to_string()
}

struct Cache;

impl Cache {
    fn get_entry(&self) -> u32 {
        0
    }
}

fn _unused() {}
