const QUERY_KEY = "licensa.query";
const MAX_QUERY_LENGTH = 2000;

export function readQueryFromLocation() {
  const params = new URLSearchParams(window.location.search);
  return (params.get("q") ?? "").trim();
}

export function rememberQuery(query) {
  window.sessionStorage.setItem(QUERY_KEY, query);
}

export function recalledQuery() {
  return window.sessionStorage.getItem(QUERY_KEY) ?? "";
}

export function goHome() {
  window.history.pushState({}, "", "/");
  window.dispatchEvent(new Event("licensa:navigate"));
}

export function goInvestigate(query) {
  const next = `/?q=${encodeURIComponent(query)}`;
  window.history.pushState({ query }, "", next);
  window.dispatchEvent(new Event("licensa:navigate"));
}

export { MAX_QUERY_LENGTH };
