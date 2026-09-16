import "./styles.css";
import { renderHome } from "./app/home.js";
import { renderInvestigate } from "./app/investigate.js";
import { readQueryFromLocation } from "./app/nav.js";

const app = document.querySelector("#app");

function render() {
  const query = readQueryFromLocation();
  if (query) {
    renderInvestigate(app, query);
    return;
  }
  renderHome(app);
}

window.addEventListener("popstate", render);
window.addEventListener("licensa:navigate", render);
render();
