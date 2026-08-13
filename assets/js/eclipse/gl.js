// Aides WebGL2 minimales. Tout le rendu de ce projet consiste en des quads
// plein cadre (un ciel, une LUT) : pas de geometrie, pas de matrices, pas de
// moteur. Ce module ne fait qu'emballer le boilerplate repetitif du contexte,
// des shaders et des textures.

// Cree le contexte WebGL2. Renvoie null si WebGL2 n'est pas disponible, ou si
// l'extension EXT_color_buffer_float manque : les LUTs de ce projet ont
// besoin de cibles de rendu flottantes, donc son absence rend le reste du
// pipeline inutilisable. C'est a l'appelant de traiter null comme "reste
// avec le HTML statique", jamais comme une erreur a remonter a l'utilisateur.
//
// `preserveDrawingBuffer` reste faux en usage normal : garder la memoire
// tampon apres composition coute une copie par image pour rien. La route
// poster (main.js) est le seul appelant a le demander, parce qu'elle doit
// relire le canevas apres coup pour l'encoder en PNG.
export function createContext(canvas, { preserveDrawingBuffer = false } = {}) {
  const gl = canvas.getContext('webgl2', {
    alpha: false,
    antialias: false,
    depth: false,
    stencil: false,
    powerPreference: 'low-power',
    preserveDrawingBuffer,
  });
  if (!gl) return null;
  if (!gl.getExtension('EXT_color_buffer_float')) return null;
  return gl;
}

// Le vertex shader est partage par tous les programmes : un seul triangle
// plein cadre, sans buffer de sommets. gl_VertexID engendre les trois coins
// (-1,-1), (3,-1), (-1,3), qui couvrent le viewport [-1,1]^2 en un triangle.
const VERTEX_SOURCE = `#version 300 es
void main() {
  vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
`;

function compile(gl, type, source, nom) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const info = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(`eclipse/gl: echec de compilation (${nom}): ${info}`);
  }
  return shader;
}

// Compile le vertex shader partage avec le fragment shader fourni, lie le
// programme, et leve une exception avec le log en cas d'echec — a la
// compilation comme a l'edition de liens. Aucun `console.error` silencieux :
// un shader casse doit casser bruyamment pendant le developpement.
export function createProgram(gl, fragmentSource, nom) {
  const vs = compile(gl, gl.VERTEX_SHADER, VERTEX_SOURCE, `${nom}:vertex`);
  const fs = compile(gl, gl.FRAGMENT_SHADER, fragmentSource, `${nom}:fragment`);
  const programme = gl.createProgram();
  gl.attachShader(programme, vs);
  gl.attachShader(programme, fs);
  gl.linkProgram(programme);
  gl.deleteShader(vs);
  gl.deleteShader(fs);
  if (!gl.getProgramParameter(programme, gl.LINK_STATUS)) {
    const info = gl.getProgramInfoLog(programme);
    gl.deleteProgram(programme);
    throw new Error(`eclipse/gl: echec d'edition de liens (${nom}): ${info}`);
  }
  return programme;
}

// Dessine le triangle plein cadre du vertex shader partage.
export function drawQuad(gl) {
  gl.drawArrays(gl.TRIANGLES, 0, 3);
}

// Descripteurs de format : on lit les enums sur le contexte plutot que de
// coder en dur leurs valeurs hexadecimales, qui varient d'une implementation
// a l'autre et ne veulent rien dire a la lecture. `gl` est toujours le
// contexte WebGL2 issu de createContext.
export function RGBA16F(gl) {
  return { internalFormat: gl.RGBA16F, format: gl.RGBA, type: gl.HALF_FLOAT };
}

export function RGB32F(gl) {
  return { internalFormat: gl.RGB32F, format: gl.RGB, type: gl.FLOAT };
}

// Cree une texture 2D avec filtrage lineaire et un habillage CLAMP_TO_EDGE
// (pas de repetition : ce sont des ciels et des LUTs, jamais des motifs).
// `format` est un descripteur produit par RGBA16F/RGB32F ci-dessus.
export function createTexture(gl, largeur, hauteur, format, donnees = null) {
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texImage2D(
    gl.TEXTURE_2D, 0, format.internalFormat, largeur, hauteur, 0,
    format.format, format.type, donnees,
  );
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.bindTexture(gl.TEXTURE_2D, null);
  return tex;
}

// Rend dans une texture via un FBO ephemere : on le cree, on l'attache, on
// appelle dessiner(), puis on le detache et on le detruit. Aucun FBO ne
// traine entre deux appels — ce module n'a pas d'etat cache.
export function renderToTexture(gl, tex, largeur, hauteur, dessiner) {
  const fbo = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  gl.viewport(0, 0, largeur, hauteur);
  dessiner();
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  gl.deleteFramebuffer(fbo);
}
