/* Crónica 33 — comportamiento del sitio (sin librerías externas). */
(function () {
  "use strict";

  var CLAVE_TEMA = "cronica33-tema";
  var CLAVE_COOKIES = "cronica33-cookies";

  function guarda(clave, valor) {
    try { localStorage.setItem(clave, valor); } catch (e) { /* modo privado */ }
  }
  function recupera(clave) {
    try { return localStorage.getItem(clave); } catch (e) { return null; }
  }

  /* ------------------------------------------------------- tema oscuro/claro */
  /* El oscuro es el de la marca y es el que sale por defecto. */

  var raiz = document.documentElement;
  var temaGuardado = recupera(CLAVE_TEMA);
  if (temaGuardado) { raiz.setAttribute("data-tema", temaGuardado); }

  var botonTema = document.getElementById("canvia-tema");
  if (botonTema) {
    botonTema.addEventListener("click", function () {
      var nuevo = raiz.getAttribute("data-tema") === "clar" ? "fosc" : "clar";
      raiz.setAttribute("data-tema", nuevo);
      guarda(CLAVE_TEMA, nuevo);
    });
  }

  /* -------------------------------------------------------------- menú móvil */

  var botonMenu = document.getElementById("obre-menu");
  var navegacion = document.getElementById("navegacio");
  if (botonMenu && navegacion) {
    botonMenu.addEventListener("click", function () {
      var abierto = navegacion.classList.toggle("obert");
      botonMenu.setAttribute("aria-expanded", abierto ? "true" : "false");
    });
  }

  /* --------------------------------------------------------------- fecha hoy */

  var cajaFecha = document.getElementById("data-avui");
  if (cajaFecha) {
    try {
      cajaFecha.textContent = new Date().toLocaleDateString("es-ES", {
        weekday: "long", day: "numeric", month: "long", year: "numeric"
      });
    } catch (e) {
      cajaFecha.textContent = "";
    }
  }

  /* ------------------------------------------------------------ copiar enlace */

  document.addEventListener("click", function (ev) {
    var boton = ev.target.closest ? ev.target.closest(".copia-enllac") : null;
    if (!boton) { return; }
    var url = boton.getAttribute("data-url") || window.location.href;
    var original = boton.textContent;
    var hecho = function () {
      boton.textContent = "Enlace copiado";
      setTimeout(function () { boton.textContent = original; }, 2000);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(hecho, function () {
        window.prompt("Copia el enlace:", url);
      });
    } else {
      window.prompt("Copia el enlace:", url);
    }
  });

  /* --------------------------------------------- publicidad y consentimiento */

  function cargaPublicidad() {
    var cliente = window.CLIENTE_ADSENSE;
    if (!cliente || document.getElementById("script-adsense")) { return; }
    var s = document.createElement("script");
    s.id = "script-adsense";
    s.async = true;
    s.crossOrigin = "anonymous";
    s.src = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=" +
      encodeURIComponent(cliente);
    document.head.appendChild(s);
    s.addEventListener("load", function () {
      var bloques = document.querySelectorAll("ins.adsbygoogle");
      for (var i = 0; i < bloques.length; i++) {
        try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch (e) { /* bloqueador */ }
      }
    });
  }

  var cajaCookies = document.getElementById("galetes");
  var decision = recupera(CLAVE_COOKIES);

  if (decision === "todo") {
    cargaPublicidad();
  } else if (!decision && cajaCookies) {
    cajaCookies.hidden = false;
  }

  if (cajaCookies) {
    var acepta = document.getElementById("accepta-galetes");
    var rechaza = document.getElementById("rebutja-galetes");
    if (acepta) {
      acepta.addEventListener("click", function () {
        guarda(CLAVE_COOKIES, "todo");
        cajaCookies.hidden = true;
        cargaPublicidad();
      });
    }
    if (rechaza) {
      rechaza.addEventListener("click", function () {
        guarda(CLAVE_COOKIES, "minimo");
        cajaCookies.hidden = true;
      });
    }
  }

  /* ------------------------------------------------------------------ buscar */

  var campo = document.getElementById("camp-cerca");
  var resultados = document.getElementById("resultats-cerca");
  if (campo && resultados) {
    var indice = null;
    var pendiente = null;

    fetch("/buscar.json")
      .then(function (r) { return r.json(); })
      .then(function (datos) {
        indice = datos;
        if (pendiente !== null) { busca(pendiente); }
      })
      .catch(function () {
        resultados.innerHTML = "<p class='buit'>No se ha podido cargar el índice de búsqueda.</p>";
      });

    function normaliza(texto) {
      return (texto || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    }

    function busca(consulta) {
      if (indice === null) { pendiente = consulta; return; }
      var q = normaliza(consulta).trim();
      if (q.length < 2) { resultados.innerHTML = ""; return; }
      var palabras = q.split(/\s+/);
      var hallados = indice.filter(function (a) {
        var texto = normaliza([a.t, a.s, a.r, a.sec, a.tags].join(" "));
        return palabras.every(function (p) { return texto.indexOf(p) !== -1; });
      });
      if (!hallados.length) {
        resultados.innerHTML = "<p class='buit'>Sin resultados para &laquo;" + consulta + "&raquo;.</p>";
        return;
      }
      resultados.innerHTML = hallados.slice(0, 40).map(function (a) {
        var img = a.img ? "<img src='" + a.img + "' alt='' loading='lazy'>" : "";
        return "<article class='resultat-cerca'>" + img +
          "<div><a class='etiqueta-seccio' href='" + a.u + "'>" + a.sec + "</a>" +
          "<h3><a href='" + a.u + "'>" + a.t + "</a></h3>" +
          "<p class='meta'>" + a.d + "</p></div></article>";
      }).join("");
    }

    var temporizador;
    campo.addEventListener("input", function () {
      clearTimeout(temporizador);
      var valor = campo.value;
      temporizador = setTimeout(function () { busca(valor); }, 120);
    });

    var inicial = new URLSearchParams(window.location.search).get("q");
    if (inicial) { campo.value = inicial; busca(inicial); }
  }
})();
