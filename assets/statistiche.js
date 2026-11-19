/* Statistiche web cookieless dell'Osservatorio (GoatCounter self-hosted su
 * stats.mxmap.it, server in UE). Niente cookie, nessun IP salvato; chi chiede
 * di non essere tracciato (Do Not Track / Global Privacy Control) non viene
 * contato. Il percorso include l'host: un solo contatore per tutti i siti
 * (mxmap.it, osservatorio.mxmap.it, analisi-spesa-ict.mxmap.it).
 * Dashboard pubblica: https://stats.mxmap.it/ — dettagli: https://osservatorio.mxmap.it/privacy/ */
(function () {
  if (navigator.doNotTrack === "1" || window.doNotTrack === "1" || navigator.globalPrivacyControl) return;
  window.goatcounter = { path: function () { return location.host + location.pathname; } };
  var s = document.createElement("script");
  s.async = true;
  s.src = "https://stats.mxmap.it/count.js";
  s.setAttribute("data-goatcounter", "https://stats.mxmap.it/count");
  document.head.appendChild(s);
})();
