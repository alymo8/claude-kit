export default async function loadData(url) {
  return url;
}

const formatName = (first, last) => `${first} ${last}`;

let parseDate = function (text) {
  return new Date(text);
};

function _hidden() {
  return 0;
}

export function normalizePath(p) {
  const trimSlashes = (s) => s.replace(/\/+$/, "");
  if (p) {
    return trimSlashes(p);
  }
  return p;
}
