---
titulo: Cómo publicar tu primera noticia en Crónica 33
subtitulo: Guía rápida para poner en marcha la redacción. Borra esta pieza cuando ya no la necesites.
seccion: sucesos
autor: Redacción Crónica 33
fecha: 2026-09-04 10:00
etiquetas: [guía, redacción]
destacado: true
---

Cada publicación del sitio es un archivo de texto dentro de `contingut/articles/`. Puedes crearlo desde el ordenador o, mucho más cómodo, desde el panel de redacción en el navegador (mira el archivo `README.md`).

## Los datos de arriba

Entre las dos líneas de guiones van los datos de la pieza:

- `titulo`: el titular.
- `subtitulo`: la entradilla que se ve bajo el titular y en portada.
- `seccion`: `sucesos`, `judicial` o `reportajes`.
- `fecha`: año-mes-día y hora. Es lo que ordena la portada.
- `imagen`: la foto de portada, por ejemplo `/media/foto.jpg`.
- `video`: un vídeo tuyo subido a `/media/`, por ejemplo `/media/clip.mp4`.
- `embed`: la dirección de una publicación de YouTube, TikTok, Instagram o X.
- `etiquetas`: temas, entre corchetes y separados por comas.
- `destacado`: pon `true` en la pieza que debe abrir la portada.
- `ultima_hora`: pon `true` y saldrá en la barra roja de arriba, en todas las páginas.
- `borrador`: pon `true` mientras no quieras publicarla.

## El cuerpo de la noticia

Debajo se escribe normal. Una línea en blanco separa los párrafos. Puedes poner **negrita**, *cursiva* y [enlaces](https://ejemplo.es).

> Las citas se marcan con el símbolo mayor que.

Para poner una imagen dentro del texto:

```
[[imagen: /media/foto.jpg | Pie de foto]]
```

Para poner un vídeo tuyo dentro del texto:

```
[[video: /media/clip.mp4 | /media/clip-portada.jpg]]
```

Y para incrustar una publicación de redes:

```
[[embed: https://www.youtube.com/watch?v=XXXXXXXX]]
```

## ¿Y después?

Guarda el archivo y el sitio se vuelve a generar solo. Si trabajas en el ordenador, ejecuta `python build.py --servir` y míralo en `http://localhost:8000`.
