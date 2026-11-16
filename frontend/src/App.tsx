import { useCallback, useEffect, useState } from "react";

type Dispositivo = {
  identificador: string;
  tipo: string;
  estado: string;
  actualizado_en: string;
};

type Evento = {
  linea: number;
  operacion: string;
  estado: string;
  detalle: string;
  dispositivos?: { identificador: string; tipo: string; estado: string }[];
};

type Historial = {
  id: number;
  instruccion: string;
  resultado: Evento | string | null;
  estado_ejecucion: string;
  fecha: string;
};

type Notificacion = { id: number; mensaje: string; fecha: string };
type Salud = { database: string };
type RespuestaEjecucion = {
  correcto: true;
  resultados: Evento[];
  dispositivos: Dispositivo[];
  instrucciones_ir: number;
};
type RespuestaAnalisis = { correcto: true; ast: unknown; instrucciones_validadas: number };
type RespuestaIR = { correcto: true; ir: unknown };
type ErrorServidor = {
  error?: { tipo?: string; descripcion?: string; linea?: number; columna?: number };
  detail?: unknown;
};
type Resultado =
  | { modo: "ejecutar"; eventos: Evento[] }
  | { modo: "analizar"; datos: unknown; cantidad: number }
  | { modo: "compilar"; datos: unknown }
  | { modo: "error"; titulo: string; descripcion: string; linea?: number; columna?: number; estado?: number };

type Modo = "ejecutar" | "analizar" | "compilar";

const EJEMPLOS = {
  basico: "ENCENDER led1\nCONSULTAR led1\nLISTAR DISPOSITIVOS",
  condicional: 'ENCENDER led1\nSI led1 == ENCENDIDO ENTONCES NOTIFICAR "LED encendido"',
  correo: 'ENVIAR CORREO A "prueba@ejemplo.com" MENSAJE "Prueba desde SmartHome"',
} as const;

const nombres: Record<string, string> = {
  led1: "LED 1",
  luz_sala: "Luz de sala",
  ventilador1: "Ventilador",
  alarma1: "Alarma",
  puerta_principal: "Puerta principal",
};

const estadosActivos = new Set(["ENCENDIDO", "ACTIVADA", "ABIERTA"]);

function comandoPara(dispositivo: Dispositivo): string {
  const activo = estadosActivos.has(dispositivo.estado);
  const comando =
    dispositivo.tipo === "ALARMA"
      ? activo ? "DESACTIVAR" : "ACTIVAR"
      : dispositivo.tipo === "PUERTA"
        ? activo ? "CERRAR" : "ABRIR"
        : activo ? "APAGAR" : "ENCENDER";
  return `${comando} ${dispositivo.identificador}`;
}

function fechaCorta(valor: string): string {
  const fecha = new Date(valor);
  return Number.isNaN(fecha.getTime())
    ? valor
    : fecha.toLocaleString("es-MX", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
}

class ErrorPeticion extends Error {
  constructor(
    message: string,
    readonly estado: number,
    readonly tipo?: string,
    readonly linea?: number,
    readonly columna?: number,
  ) {
    super(message);
    this.name = "ErrorPeticion";
  }
}

async function solicitar<T>(ruta: string, init?: RequestInit): Promise<T> {
  let respuesta: Response;
  try {
    respuesta = await fetch(ruta, { cache: "no-store", ...init });
  } catch {
    throw new ErrorPeticion("No se pudo establecer conexión con FastAPI.", 0, "CONEXION");
  }

  let cuerpo: unknown = null;
  try {
    cuerpo = await respuesta.json();
  } catch {
    // Si la respuesta no es JSON, mostramos el estado HTTP.
  }

  if (!respuesta.ok) {
    const datos = (cuerpo ?? {}) as ErrorServidor;
    const detalle = datos.error?.descripcion
      ?? (typeof datos.detail === "string" ? datos.detail : undefined)
      ?? `Error HTTP ${respuesta.status}`;
    throw new ErrorPeticion(
      detalle,
      respuesta.status,
      datos.error?.tipo,
      datos.error?.linea,
      datos.error?.columna,
    );
  }

  return cuerpo as T;
}

function IconoDispositivo({ tipo }: { tipo: string }) {
  if (tipo === "LED" || tipo === "LUZ") {
    return (
      <svg viewBox="0 0 72 72" role="img" aria-label="Luz simulada">
        <circle className="light-bulb" cx="36" cy="28" r="17" />
        <path d="M27 41 L27 49 L45 49 L45 41 M29 54 H43 M32 58 H40" />
        <path d="M24 27 Q36 17 48 27" />
      </svg>
    );
  }
  if (tipo === "VENTILADOR") {
    return (
      <svg viewBox="0 0 72 72" role="img" aria-label="Ventilador simulado">
        <circle cx="36" cy="33" r="25" />
        <g className="fan-blades">
          <path d="M36 32 C31 25 29 12 39 15 C49 18 42 30 36 32 Z" />
          <path d="M36 32 C44 30 57 33 52 43 C47 51 38 40 36 32 Z" />
          <path d="M36 32 C35 40 25 50 19 43 C14 35 27 31 36 32 Z" />
        </g>
        <circle cx="36" cy="33" r="4" />
        <path d="M36 58 V65 M25 65 H47" />
      </svg>
    );
  }
  if (tipo === "ALARMA") {
    return (
      <svg viewBox="0 0 72 72" role="img" aria-label="Alarma simulada">
        <path d="M18 49 H54 L49 42 V29 A13 13 0 0 0 23 29 V42 Z" />
        <path d="M31 53 Q36 60 41 53 M36 9 V15 M12 26 L17 29 M60 26 L55 29" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 72 72" role="img" aria-label="Puerta simulada">
      <rect x="19" y="10" width="34" height="52" rx="1" />
      <path className="door-leaf" d="M24 14 L47 18 V55 L24 59 Z" />
      <circle cx="42" cy="37" r="2" />
    </svg>
  );
}

function TarjetaDispositivo({
  dispositivo,
  ocupado,
  alControlar,
}: {
  dispositivo: Dispositivo;
  ocupado: boolean;
  alControlar: (codigo: string) => void;
}) {
  const activo = estadosActivos.has(dispositivo.estado);
  const comando = comandoPara(dispositivo);

  return (
    <article className={`dispositivo ${activo ? "dispositivo-activo" : ""}`}>
      <div className="dispositivo-ilustracion">
        <IconoDispositivo tipo={dispositivo.tipo} />
      </div>
      <div className="dispositivo-datos">
        <div className="dispositivo-superior">
          <h3>{nombres[dispositivo.identificador] ?? dispositivo.identificador}</h3>
          <span className={`estado ${activo ? "estado-activo" : "estado-inactivo"}`}>
            {dispositivo.estado}
          </span>
        </div>
        <p>{dispositivo.tipo} · <code>{dispositivo.identificador}</code></p>
        <button
          type="button"
          className="boton-control"
          disabled={ocupado}
          onClick={() => alControlar(comando)}
        >
          {comando.split(" ")[0]}
        </button>
      </div>
    </article>
  );
}

export default function App() {
  const [dispositivos, setDispositivos] = useState<Dispositivo[]>([]);
  const [historial, setHistorial] = useState<Historial[]>([]);
  const [notificaciones, setNotificaciones] = useState<Notificacion[]>([]);
  const [codigo, setCodigo] = useState<string>(EJEMPLOS.basico);
  const [ejemplo, setEjemplo] = useState<keyof typeof EJEMPLOS>("basico");
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [conectado, setConectado] = useState(false);
  const [errorCarga, setErrorCarga] = useState<string | null>(null);
  const [ultimaActualizacion, setUltimaActualizacion] = useState<string | null>(null);

  const actualizar = useCallback(async () => {
    const [rDispositivos, rHistorial, rNotificaciones, rSalud] = await Promise.allSettled([
      solicitar<{ dispositivos: Dispositivo[] }>("/api/dispositivos"),
      solicitar<{ historial: Historial[] }>("/api/historial?limite=30"),
      solicitar<{ notificaciones: Notificacion[] }>("/api/notificaciones?limite=30"),
      solicitar<Salud>("/api/health"),
    ]);

    if (rDispositivos.status === "fulfilled") {
      setDispositivos(rDispositivos.value.dispositivos);
    }
    if (rHistorial.status === "fulfilled") {
      setHistorial(rHistorial.value.historial);
    }
    if (rNotificaciones.status === "fulfilled") {
      setNotificaciones(rNotificaciones.value.notificaciones);
    }

    const disponible = rDispositivos.status === "fulfilled"
      && rSalud.status === "fulfilled"
      && rSalud.value.database === "connected";
    setConectado(disponible);
    setErrorCarga(disponible ? null : "No fue posible consultar el sistema. Verifica FastAPI y PostgreSQL.");
    if (disponible) setUltimaActualizacion(new Date().toLocaleTimeString("es-MX"));
    setCargando(false);
  }, []);

  useEffect(() => {
    void actualizar();
    const intervalo = window.setInterval(() => { void actualizar(); }, 15000);
    return () => window.clearInterval(intervalo);
  }, [actualizar]);

  async function procesar(modo: Modo, fuente = codigo) {
    if (ocupado || !fuente.trim()) return;
    setOcupado(true);
    setResultado(null);

    const rutas: Record<Modo, string> = {
      ejecutar: "/api/ejecutar",
      analizar: "/api/analizar",
      compilar: "/api/compilar",
    };

    try {
      const opciones = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ codigo: fuente }),
      };
      if (modo === "ejecutar") {
        const respuesta = await solicitar<RespuestaEjecucion>(rutas[modo], opciones);
        setResultado({ modo: "ejecutar", eventos: respuesta.resultados });
        setDispositivos(respuesta.dispositivos);
        await actualizar();
      } else if (modo === "analizar") {
        const respuesta = await solicitar<RespuestaAnalisis>(rutas[modo], opciones);
        setResultado({ modo: "analizar", datos: respuesta.ast, cantidad: respuesta.instrucciones_validadas });
      } else {
        const respuesta = await solicitar<RespuestaIR>(rutas[modo], opciones);
        setResultado({ modo: "compilar", datos: respuesta.ir });
      }
    } catch (error) {
      if (error instanceof ErrorPeticion) {
        setResultado({
          modo: "error",
          titulo: error.tipo ? `Error ${error.tipo.toLowerCase()}` : "Error al procesar",
          descripcion: error.message,
          linea: error.linea,
          columna: error.columna,
          estado: error.estado,
        });
      } else {
        setResultado({ modo: "error", titulo: "Error", descripcion: "Ocurrió un problema inesperado." });
      }
    } finally {
      setOcupado(false);
    }
  }

  function cargarEjemplo(valor: keyof typeof EJEMPLOS) {
    setEjemplo(valor);
    setCodigo(EJEMPLOS[valor]);
    setResultado(null);
  }

  const activos = dispositivos.filter((d) => estadosActivos.has(d.estado)).length;

  return (
    <div className="aplicacion">
      <header className="encabezado">
        <div className="encabezado-contenido">
          <div className="marca">
            <span className="marca-simbolo" aria-hidden="true">SH</span>
            <div>
              <strong>SmartHome</strong>
              <span>Proyecto integrador · Lenguajes y Autómatas II</span>
            </div>
          </div>
          <div className="encabezado-derecha">
            <span className={`conexion ${conectado ? "conexion-activa" : "conexion-inactiva"}`}>
              <span className="conexion-punto" aria-hidden="true" />
              {conectado ? "Servidor conectado" : cargando ? "Comprobando..." : "Sin conexión"}
            </span>
            <button type="button" className="boton boton-secundario" onClick={() => void actualizar()}>
              Actualizar
            </button>
          </div>
        </div>
      </header>

      <main className="contenido">
        <div className="titulo-pagina">
          <div>
            <h1>Panel de control</h1>
            <p>Control de dispositivos simulados mediante instrucciones SmartHome Script.</p>
          </div>
          <span className="version">SmartHome Script 1.0</span>
        </div>

        {errorCarga && <div role="alert" className="alerta alerta-error">{errorCarga}</div>}

        <div className="resumen">
          <span><strong>{dispositivos.length}</strong> dispositivos registrados</span>
          <span><strong>{activos}</strong> activos</span>
          <span><strong>{historial.length}</strong> eventos recientes</span>
          <span className="actualizacion">{ultimaActualizacion ? `Actualizado: ${ultimaActualizacion}` : ""}</span>
        </div>

        <div className="principal-grid">
          <section className="panel panel-dispositivos" aria-labelledby="titulo-dispositivos">
            <div className="panel-cabecera">
              <div>
                <h2 id="titulo-dispositivos">Dispositivos</h2>
                <p>El estado mostrado se obtiene de PostgreSQL.</p>
              </div>
            </div>
            <div className="lista-dispositivos">
              {cargando && dispositivos.length === 0 ? (
                <p className="sin-registros">Cargando dispositivos...</p>
              ) : dispositivos.length === 0 ? (
                <p className="sin-registros">No hay dispositivos disponibles.</p>
              ) : dispositivos.map((d) => (
                <TarjetaDispositivo
                  key={d.identificador}
                  dispositivo={d}
                  ocupado={ocupado}
                  alControlar={(comando) => void procesar("ejecutar", comando)}
                />
              ))}
            </div>
          </section>

          <section className="panel panel-consola" aria-labelledby="titulo-consola">
            <div className="panel-cabecera">
              <div>
                <h2 id="titulo-consola">Consola de instrucciones</h2>
                <p>Escribe una o varias instrucciones, una por línea.</p>
              </div>
            </div>

            <label className="etiqueta" htmlFor="editor-codigo">Programa SmartHome</label>
            <textarea
              id="editor-codigo"
              className="editor"
              spellCheck={false}
              maxLength={20000}
              value={codigo}
              onChange={(evento) => setCodigo(evento.target.value)}
              onKeyDown={(evento) => {
                if ((evento.ctrlKey || evento.metaKey) && evento.key === "Enter") {
                  evento.preventDefault();
                  void procesar("ejecutar");
                }
              }}
              placeholder="ENCENDER led1&#10;CONSULTAR led1"
            />
            <div className="editor-ayuda">
              <span>Comandos en mayúsculas · Ctrl + Enter para ejecutar</span>
              <span>{codigo.split("\n").length} líneas</span>
            </div>

            <div className="ejemplos">
              <label htmlFor="selector-ejemplo">Ejemplos</label>
              <select
                id="selector-ejemplo"
                value={ejemplo}
                onChange={(evento) => cargarEjemplo(evento.target.value as keyof typeof EJEMPLOS)}
              >
                <option value="basico">Encender, consultar y listar</option>
                <option value="condicional">Condición y notificación</option>
                <option value="correo">Correo de prueba (Mailpit)</option>
              </select>
              <button type="button" className="boton boton-secundario" onClick={() => cargarEjemplo(ejemplo)}>
                Cargar
              </button>
            </div>

            <div className="acciones">
              <button
                type="button"
                className="boton boton-principal"
                disabled={ocupado || !codigo.trim()}
                onClick={() => void procesar("ejecutar")}
              >
                {ocupado ? "Procesando..." : "Ejecutar"}
              </button>
              <button type="button" className="boton boton-secundario" disabled={ocupado || !codigo.trim()} onClick={() => void procesar("analizar")}>
                Validar
              </button>
              <button type="button" className="boton boton-secundario" disabled={ocupado || !codigo.trim()} onClick={() => void procesar("compilar")}>
                Ver IR
              </button>
              <button type="button" className="boton boton-texto" disabled={ocupado} onClick={() => { setCodigo(""); setResultado(null); }}>
                Limpiar
              </button>
            </div>

            <div className="bloque-resultados" aria-live="polite">
              <div className="resultados-cabecera">
                <h3>Resultado</h3>
                {resultado && <button className="boton-enlace" type="button" onClick={() => setResultado(null)}>Borrar resultado</button>}
              </div>

              {resultado === null ? (
                <p className="sin-resultado">Aquí aparecerá el resultado de la ejecución o el análisis.</p>
              ) : resultado.modo === "error" ? (
                <div className="resultado-error" role="alert">
                  <strong>{resultado.titulo}</strong>
                  <p>{resultado.descripcion}</p>
                  {resultado.linea != null && (
                    <small>Línea {resultado.linea}{resultado.columna != null ? `, columna ${resultado.columna}` : ""}</small>
                  )}
                </div>
              ) : resultado.modo === "ejecutar" ? (
                <div className="resultado-exito">
                  <p className="resultado-aviso">Programa ejecutado · {resultado.eventos.length} resultados registrados</p>
                  {resultado.eventos.length === 0 && <p>No había instrucciones para ejecutar.</p>}
                  <ul className="eventos">
                    {resultado.eventos.map((evento, indice) => (
                      <li key={indice} className={evento.estado === "OMITIDA" ? "evento-omitido" : ""}>
                        <span className="evento-linea">Línea {evento.linea}</span>
                        <span className="evento-texto">{evento.detalle}</span>
                        <span className="evento-estado">{evento.estado}</span>
                        {evento.dispositivos && (
                          <details className="detalle-listado">
                            <summary>Ver lista de dispositivos</summary>
                            <ul>{evento.dispositivos.map((d) => <li key={d.identificador}>{d.identificador}: {d.estado}</li>)}</ul>
                          </details>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="resultado-inspeccion">
                  <p className="resultado-aviso">
                    {resultado.modo === "analizar"
                      ? `Análisis correcto · ${resultado.cantidad} instrucciones válidas`
                      : "Código intermedio generado correctamente"}
                  </p>
                  <pre>{JSON.stringify(resultado.datos, null, 2)}</pre>
                </div>
              )}
            </div>
          </section>
        </div>

        <div className="actividad-grid">
          <section className="panel" aria-labelledby="titulo-historial">
            <div className="panel-cabecera">
              <div>
                <h2 id="titulo-historial">Historial de operaciones</h2>
                <p>Últimos 30 registros guardados en PostgreSQL.</p>
              </div>
            </div>
            <div className="tabla-contenedor">
              <table>
                <thead>
                  <tr><th>Fecha</th><th>Instrucción</th><th>Resultado</th><th>Estado</th></tr>
                </thead>
                <tbody>
                  {historial.map((item) => (
                    <tr key={item.id}>
                      <td className="celda-fecha">{fechaCorta(item.fecha)}</td>
                      <td><code>{item.instruccion}</code></td>
                      <td>{typeof item.resultado === "object" && item.resultado !== null ? item.resultado.detalle : item.resultado ?? "—"}</td>
                      <td><span className={item.estado_ejecucion === "EXITOSA" ? "texto-exito" : "texto-tenue"}>{item.estado_ejecucion}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {historial.length === 0 && <p className="sin-registros">No hay operaciones registradas.</p>}
            </div>
          </section>

          <section className="panel" aria-labelledby="titulo-notificaciones">
            <div className="panel-cabecera">
              <div>
                <h2 id="titulo-notificaciones">Notificaciones</h2>
                <p>Mensajes generados con NOTIFICAR.</p>
              </div>
            </div>
            <div className="lista-notificaciones">
              {notificaciones.length === 0 ? (
                <p className="sin-registros">No hay notificaciones registradas.</p>
              ) : notificaciones.map((item) => (
                <article key={item.id} className="notificacion">
                  <p>{item.mensaje}</p>
                  <time>{fechaCorta(item.fecha)}</time>
                </article>
              ))}
            </div>
            <div className="ayuda-correo">
              Para probar ENVIAR CORREO, utiliza el ejemplo de la consola y consulta{" "}
              <a href="http://localhost:8025" target="_blank" rel="noreferrer">Mailpit (SMTP de pruebas)</a>.
            </div>
          </section>
        </div>
        <footer className="pie">SmartHome · Simulación de dispositivos · React + FastAPI + PostgreSQL</footer>
      </main>
    </div>
  );
}
