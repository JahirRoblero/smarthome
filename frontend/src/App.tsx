import { useCallback, useEffect, useState } from "react";
import logo from "../src/assets/logoSmarthHome.png";
import alarmaEncendida from "../src/assets/alarmaEncendida.png";
import alarmaApagada from "../src/assets/alarmaApagada.png";
import luzEncendida from "../src/assets/luzEncendida.png";
import luzApagada from "../src/assets/luzApagada.png";
import puertaAbierta from "../src/assets/PuertaAbierta.png";
import puertaCerrada from "../src/assets/puertaCerrada.png";
import ventiladorEncendido from "../src/assets/ventiladorEncendido.png";
import ventiladorApagado from "../src/assets/ventiladorApagado.png";

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
  optimizada?: boolean;
  dispositivo?: string;
  valor?: string;
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
type ResumenOptimizacion = {
  habilitada: boolean;
  asignaciones_originales: number;
  escrituras_fisicas: number;
  escrituras_evitadas: number;
  redundantes: number;
  sobrescritas: number;
  evitadas_por_estado?: number;
};

type RespuestaEjecucion = {
  optimizacion: ResumenOptimizacion;
  correcto: true;
  resultados: Evento[];
  dispositivos: Dispositivo[];
  instrucciones_ir: number;
};
type RespuestaAnalisis = {
  correcto: true;
  ast: unknown;
  instrucciones_validadas: number;
};
type RespuestaIR = { correcto: true; ir: unknown };
type ErrorServidor = {
  error?: {
    tipo?: string;
    descripcion?: string;
    linea?: number;
    columna?: number;
  };
  detail?: unknown;
};
type Resultado =
  | { modo: "ejecutar"; eventos: Evento[]; optimizacion: ResumenOptimizacion }
  | { modo: "analizar"; datos: unknown; cantidad: number }
  | { modo: "compilar"; datos: unknown }
  | {
      modo: "error";
      titulo: string;
      descripcion: string;
      tipo?: string;
      instruccion?: string;
      linea?: number;
      columna?: number;
      estado?: number;
    };

type Modo = "ejecutar" | "analizar" | "compilar";

const EJEMPLOS = {
  basico: "ENCENDER led1\nCONSULTAR led1\nLISTAR DISPOSITIVOS",
  condicional:
    'ENCENDER led1\nSI led1 == ENCENDIDO ENTONCES NOTIFICAR "LED encendido"',
  correo:
    'ENVIAR CORREO A "prueba@ejemplo.com" MENSAJE "Prueba desde SmartHome"',
} as const;

// Ejemplos comprobados contra la gramática de SmartHome Script 1.0.
const GUIA_COMANDOS = [
  {
    titulo: "Control de dispositivos",
    descripcion: "Las acciones dependen del tipo de dispositivo.",
    comandos: [
      { nombre: "Encender", codigo: "ENCENDER led1", detalle: "LED, luces o ventiladores" },
      { nombre: "Apagar", codigo: "APAGAR luz_sala", detalle: "LED, luces o ventiladores" },
      { nombre: "Activar", codigo: "ACTIVAR alarma1", detalle: "Activar una alarma" },
      { nombre: "Desactivar", codigo: "DESACTIVAR alarma1", detalle: "Desactivar una alarma" },
      { nombre: "Abrir", codigo: "ABRIR puerta_principal", detalle: "Abrir una puerta" },
      { nombre: "Cerrar", codigo: "CERRAR puerta_principal", detalle: "Cerrar una puerta" },
    ],
  },
  {
    titulo: "Consultar dispositivos",
    descripcion: "Leer estados sin modificar los dispositivos.",
    comandos: [
      { nombre: "Consultar", codigo: "CONSULTAR led1", detalle: "Ver el estado de un dispositivo" },
      { nombre: "Listar", codigo: "LISTAR DISPOSITIVOS", detalle: "Mostrar todos los dispositivos" },
    ],
  },
  {
    titulo: "Avisos y correo",
    descripcion: "Generar avisos o enviar mensajes por correo electrónico.",
    comandos: [
      { nombre: "Notificar", codigo: 'NOTIFICAR "Movimiento detectado"', detalle: "Crear una notificación interna" },
      { nombre: "Enviar correo", codigo: 'ENVIAR CORREO A "correo@ejemplo.com" MENSAJE "Alerta de SmartHome"', detalle: "Sustituye el destinatario por un correo real" },
    ],
  },
  {
    titulo: "Condiciones",
    descripcion: "Ejecutar una instrucción solo cuando se cumpla una condición.",
    comandos: [
      { nombre: "Si... entonces", codigo: 'SI led1 == ENCENDIDO ENTONCES NOTIFICAR "El LED está encendido"', detalle: "Comparar un estado con ==" },
      { nombre: "Control condicionado", codigo: "SI alarma1 == ACTIVADA ENTONCES ENCENDER led1", detalle: "Ejecutar una acción según un estado" },
    ],
  },
] as const;

const COMANDOS_RAPIDOS = ["ENCENDER led1", "CONSULTAR led1", "LISTAR DISPOSITIVOS"] as const;

const nombres: Record<string, string> = {
  led1: "LED 1",
  luz_sala: "Luz de sala",
  ventilador1: "Ventilador",
  alarma1: "Alarma",
  puerta_principal: "Puerta principal",
};

const estadosActivos = new Set(["ENCENDIDO", "ACTIVADA", "ABIERTA"]);

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
    throw new ErrorPeticion(
      "No se pudo establecer conexión con FastAPI.",
      0,
      "CONEXION",
    );
  }

  let cuerpo: unknown = null;
  try {
    cuerpo = await respuesta.json();
  } catch {}

  if (!respuesta.ok) {
    const datos = (cuerpo ?? {}) as ErrorServidor;
    const detalle =
      datos.error?.descripcion ??
      (typeof datos.detail === "string" ? datos.detail : undefined) ??
      `Error HTTP ${respuesta.status}`;
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

function IconoDispositivo({
  tipo,
  ocupado,
}: {
  tipo: string;
  ocupado: boolean;
}) {
  if (tipo === "LED" || tipo === "LUZ") {
    return <img className="alarma" src={ocupado ? luzEncendida : luzApagada} />;
  }
  if (tipo === "VENTILADOR") {
    return (
      <img
        className="alarma"
        src={ocupado ? ventiladorEncendido : ventiladorApagado}
      />
    );
  }
  if (tipo === "ALARMA") {
    return (
      <img className="alarma" src={ocupado ? alarmaEncendida : alarmaApagada} />
    );
  }
  return (
    <img className="alarma" src={ocupado ? puertaAbierta : puertaCerrada} />
  );
}

function TarjetaDispositivo({ dispositivo }: { dispositivo: Dispositivo }) {
  const activo = estadosActivos.has(dispositivo.estado);

  return (
    <article className={`dispositivo ${activo ? "dispositivo-activo" : ""}`}>
      <div className="dispositivo-ilustracion">
        <IconoDispositivo ocupado={activo} tipo={dispositivo.tipo} />
      </div>
      <div className="dispositivo-datos">
        <div className="dispositivo-superior">
          <h3>{dispositivo.identificador}</h3>
          <span
            className={`estado ${activo ? "estado-activo" : "estado-inactivo"}`}
          >
            {dispositivo.estado}
          </span>
        </div>
      </div>
    </article>
  );
}

const accionesPorEstado: Record<string, string> = {
  ENCENDIDO: "ENCENDER",
  APAGADO: "APAGAR",
  ACTIVADA: "ACTIVAR",
  DESACTIVADA: "DESACTIVAR",
  ABIERTA: "ABRIR",
  CERRADA: "CERRAR",
};

function DetalleEjecucion({
  evento,
  dispositivos,
}: {
  evento: Evento;
  dispositivos: Dispositivo[];
}) {
  const identificador = evento.dispositivo;
  const valor = evento.valor;

  if (!identificador || !valor) {
    return <span className="evento-texto">{evento.detalle}</span>;
  }

  const tipo = dispositivos.find(
    (dispositivo) => dispositivo.identificador === identificador,
  )?.tipo;
  const instruccion = accionesPorEstado[valor] ?? evento.operacion;
  const nombre = nombres[identificador] ?? identificador;
  const estadoLegible =
    tipo === "LUZ" && valor === "ENCENDIDO"
      ? "encendida"
      : tipo === "LUZ" && valor === "APAGADO"
        ? "apagada"
        : valor.toLowerCase();

  return (
    <div className="evento-completo">
      <div className="evento-reconocimiento">
        <p>
          <span>Instrucción reconocida:</span>
          <strong>{instruccion}</strong>
        </p>
        <p>
          <span>Dispositivo:</span>
          <strong>{identificador}</strong>
        </p>
        <p>
          <span>Validación:</span>
          <strong className="valor-correcto">CORRECTA</strong>
        </p>
        <p>
          <span>Ejecución:</span>
          <strong className={evento.estado === "OMITIDA" ? "valor-omitido" : "valor-correcto"}>
            {evento.estado}
          </strong>
        </p>
      </div>
      {evento.optimizada ? (
        <p className="evento-sin-escritura">
          Optimización aplicada: no se realizó UPDATE del dispositivo
          ni se guardó esta instrucción en el historial.
        </p>
      ) : (
        <p className="evento-confirmacion">
          {nombre} {estadoLegible} correctamente.
        </p>
      )}
    </div>
  );
}

export default function App() {
  const [dispositivos, setDispositivos] = useState<Dispositivo[]>([]);
  const [historial, setHistorial] = useState<Historial[]>([]);
  const [notificaciones, setNotificaciones] = useState<Notificacion[]>([]);
  const [codigo, setCodigo] = useState<string>(EJEMPLOS.basico);
  const [guiaAbierta, setGuiaAbierta] = useState(false);
  const [optimizar, setOptimizar] = useState(true);
  const [ejemplo, setEjemplo] = useState<keyof typeof EJEMPLOS>("basico");
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [conectado, setConectado] = useState(false);
  const [errorCarga, setErrorCarga] = useState<string | null>(null);

  const actualizar = useCallback(async () => {
    const [rDispositivos, rHistorial, rNotificaciones, rSalud] =
      await Promise.allSettled([
        solicitar<{ dispositivos: Dispositivo[] }>("/api/dispositivos"),
        solicitar<{ historial: Historial[] }>("/api/historial?limite=30"),
        solicitar<{ notificaciones: Notificacion[] }>(
          "/api/notificaciones?limite=30",
        ),
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

    const disponible =
      rDispositivos.status === "fulfilled" &&
      rSalud.status === "fulfilled" &&
      rSalud.value.database === "connected";
    setConectado(disponible);
    setErrorCarga(
      disponible
        ? null
        : "No fue posible consultar el sistema. Verifica FastAPI y PostgreSQL.",
    );
    setCargando(false);
  }, []);

  useEffect(() => {
    void actualizar();
    const intervalo = window.setInterval(() => {
      void actualizar();
    }, 15000);
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
        body: JSON.stringify(
          modo === "analizar"
            ? { codigo: fuente }
            : { codigo: fuente, optimizar },
        ),
      };
      if (modo === "ejecutar") {
        const respuesta = await solicitar<RespuestaEjecucion>(
          rutas[modo],
          opciones,
        );
        setResultado({
          modo: "ejecutar",
          eventos: respuesta.resultados,
          optimizacion: respuesta.optimizacion,
        });
        setDispositivos(respuesta.dispositivos);
        await actualizar();
      } else if (modo === "analizar") {
        const respuesta = await solicitar<RespuestaAnalisis>(
          rutas[modo],
          opciones,
        );
        setResultado({
          modo: "analizar",
          datos: respuesta.ast,
          cantidad: respuesta.instrucciones_validadas,
        });
      } else {
        const respuesta = await solicitar<RespuestaIR>(rutas[modo], opciones);
        setResultado({ modo: "compilar", datos: respuesta.ir });
      }
    } catch (error) {
      if (error instanceof ErrorPeticion) {
        setResultado({
          modo: "error",
          titulo:
            error.tipo === "SEMANTICO"
              ? "Error semántico"
              : error.tipo === "SINTACTICO"
                ? "Error sintáctico"
                : error.tipo === "LEXICO"
                  ? "Error léxico"
                  : error.tipo
                    ? `Error ${error.tipo.toLowerCase()}`
                    : "Error al procesar",
          descripcion: error.message,
          tipo: error.tipo,
          instruccion:
            error.linea != null
              ? fuente.split(/\r?\n/)[error.linea - 1]?.trim()
              : undefined,
          linea: error.linea,
          columna: error.columna,
          estado: error.estado,
        });
      } else {
        setResultado({
          modo: "error",
          titulo: "Error",
          descripcion: "Ocurrió un problema inesperado.",
        });
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

  function usarComandoAyuda(comando: string) {
    // Cargar solo en el editor: nunca ejecutar instrucciones desde la guía.
    setCodigo(comando);
    setResultado(null);
    document.getElementById("editor-codigo")?.focus();
  }

  const activos = dispositivos.filter((d) =>
    estadosActivos.has(d.estado),
  ).length;

  return (
    <div className="aplicacion">
      <header className="encabezado">
        <div className="encabezado-contenido">
          <div className="marca">
            <img className="logoSmarthHome" src={logo}></img>
            <div className="contenedorLogo">
              <strong>SmartHome</strong>
              <span>Proyecto integrador · Lenguajes y Autómatas II</span>
            </div>
          </div>
          <div className="encabezado-derecha">
            <span
              className={`conexion ${conectado ? "conexion-activa" : "conexion-inactiva"}`}
            ></span>
          </div>
        </div>
      </header>

      <main className="contenido">
        <div className="titulo-pagina">
          <div>
            <h1 className="principal">Panel de control Smarthome</h1>
            <p>
              Control de dispositivos simulados mediante instrucciones SmartHome
              Script.
            </p>
          </div>
        </div>

        <section className="guia-script" aria-labelledby="titulo-guia-script">
          <div className="guia-script-cabecera">
            <div>
              <span className="guia-script-sobrelinea">¿Primera vez en SmartHome?</span>
              <h2 id="titulo-guia-script">Guía rápida de comandos</h2>
              <p>
                Controla los dispositivos escribiendo instrucciones en mayúsculas.
                Los nombres de dispositivos van en minúsculas y los mensajes entre comillas.
              </p>
            </div>
            <button
              type="button"
              className="guia-script-desplegar"
              aria-expanded={guiaAbierta}
              aria-controls="guia-script-detalle"
              onClick={() => setGuiaAbierta((abierta) => !abierta)}
            >
              {guiaAbierta ? "Ocultar guía" : "Ver todos los comandos"}
              <span aria-hidden="true">{guiaAbierta ? "▴" : "▾"}</span>
            </button>
          </div>
          <div className="guia-script-rapidos">
            <span>Prueba uno:</span>
            {COMANDOS_RAPIDOS.map((comando) => (
              <button
                type="button"
                className="guia-script-ejemplo"
                key={comando}
                onClick={() => usarComandoAyuda(comando)}
                title="Cargar en la consola sin ejecutar"
              >
                <code>{comando}</code>
              </button>
            ))}
          </div>
          <div
            id="guia-script-detalle"
            className="guia-script-detalle"
            hidden={!guiaAbierta}
          >
            <div className="guia-script-grupos">
              {GUIA_COMANDOS.map((grupo) => (
                <div className="guia-script-grupo" key={grupo.titulo}>
                  <h3>{grupo.titulo}</h3>
                  <p>{grupo.descripcion}</p>
                  <ul>
                    {grupo.comandos.map((comando) => (
                      <li key={comando.codigo}>
                        <div className="guia-script-comando">
                          <strong>{comando.nombre}</strong>
                          <code>{comando.codigo}</code>
                          <span>{comando.detalle}</span>
                        </div>
                        <button
                          type="button"
                          className="guia-script-usar"
                          onClick={() => usarComandoAyuda(comando.codigo)}
                          title="Cargar en la consola sin ejecutar"
                        >
                          Usar
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <p className="guia-script-nota">
              Cada instrucción va en una línea. Puedes combinar varias líneas.
              Cambia los identificadores según los dispositivos registrados.
              Los ejemplos solo se cargan en la consola: pulsa Ejecutar cuando estén listos.
            </p>
          </div>
        </section>

        {errorCarga && (
          <div role="alert" className="alerta alerta-error">
            {errorCarga}
          </div>
        )}

        <div className="resumen">
          <span>
            <strong>{dispositivos.length}</strong> dispositivos registrados
          </span>
          <span>
            <strong>{activos}</strong> activos
          </span>
        </div>

        <div className="principal-grid">
          <section
            className="panel panel-dispositivos"
            aria-labelledby="titulo-dispositivos"
          >
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
                <p className="sin-registros">
                  No hay dispositivos disponibles.
                </p>
              ) : (
                dispositivos.map((d) => (
                  <TarjetaDispositivo key={d.identificador} dispositivo={d} />
                ))
              )}
            </div>
          </section>

          <section
            className="panel panel-consola"
            aria-labelledby="titulo-consola"
          >
            <div className="panel-cabecera">
              <div>
                <h2 id="titulo-consola">Consola de instrucciones</h2>
                <p>Escribe una o varias instrucciones, una por línea.</p>
              </div>
            </div>

            <label className="etiqueta" htmlFor="editor-codigo">
              Terminal SmartHome
            </label>
            <textarea
              id="editor-codigo"
              className="editor"
              spellCheck={false}
              maxLength={20000}
              value={codigo}
              onChange={(evento) => setCodigo(evento.target.value)}
              onKeyDown={(evento) => {
                if (
                  (evento.ctrlKey || evento.metaKey) &&
                  evento.key === "Enter"
                ) {
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
                onChange={(evento) =>
                  cargarEjemplo(evento.target.value as keyof typeof EJEMPLOS)
                }
              >
                <option value="basico">Encender, consultar y listar</option>
                <option value="condicional">Condición y notificación</option>
                <option value="correo">Enviar correo (Mailpit o Resend)</option>
              </select>
              <button
                type="button"
                className="boton boton-secundario"
                onClick={() => cargarEjemplo(ejemplo)}
              >
                Cargar
              </button>
            </div>

            <label className="opcion-optimizacion">
              <input
                type="checkbox"
                checked={optimizar}
                onChange={(evento) => setOptimizar(evento.target.checked)}
                disabled={ocupado}
              />
              Optimizar escrituras de estado 
            </label>

            <div className="acciones">
              <button
                type="button"
                className="boton boton-principal"
                disabled={ocupado || !codigo.trim()}
                onClick={() => void procesar("ejecutar")}
              >
                {ocupado ? "Procesando..." : "Ejecutar"}
              </button>
              <button
                type="button"
                className="boton boton-secundario"
                disabled={ocupado || !codigo.trim()}
                onClick={() => void procesar("analizar")}
              >
                Validar
              </button>
              <button
                type="button"
                className="boton boton-secundario"
                disabled={ocupado || !codigo.trim()}
                onClick={() => void procesar("compilar")}
              >
                Ver IR
              </button>
              <button
                type="button"
                className="boton boton-texto"
                disabled={ocupado}
                onClick={() => {
                  setCodigo("");
                  setResultado(null);
                }}
              >
                Limpiar
              </button>
            </div>

            <div className="bloque-resultados" aria-live="polite">
              <div className="resultados-cabecera">
                <h3>Resultado</h3>
                {resultado && (
                  <button
                    className="boton-enlace"
                    type="button"
                    onClick={() => setResultado(null)}
                  >
                    Borrar resultado
                  </button>
                )}
              </div>

              {resultado === null ? (
                <p className="sin-resultado">
                  Aquí aparecerá el resultado de la ejecución o el análisis.
                </p>
              ) : resultado.modo === "error" ? (
                <div className="resultado-error" role="alert">
                  <strong>{resultado.titulo}</strong>
                  {resultado.instruccion && (
                    <p className="error-instruccion">
                      Instrucción recibida: <code>{resultado.instruccion}</code>
                    </p>
                  )}
                  {resultado.tipo === "SEMANTICO" && (
                    <p className="error-validacion">
                      Validación: <strong>ERROR</strong>
                    </p>
                  )}
                  <p className="error-descripcion">{resultado.descripcion}</p>
                  {resultado.linea != null && (
                    <small>
                      Línea {resultado.linea}
                      {resultado.columna != null
                        ? `, columna ${resultado.columna}`
                        : ""}
                    </small>
                  )}
                </div>
              ) : resultado.modo === "ejecutar" ? (
                <div className="resultado-exito">
                  <p className="resultado-aviso">
                    Programa procesado · {resultado.eventos.length} resultados
                    generados
                  </p>
                  {resultado.optimizacion && (
                    <p className="resumen-optimizacion">
                      {resultado.optimizacion.habilitada
                        ? `Optimización: ${resultado.optimizacion.escrituras_evitadas} escrituras evitadas (${resultado.optimizacion.redundantes} redundantes en IR, ${resultado.optimizacion.sobrescritas} sobrescritas en IR, ${resultado.optimizacion.evitadas_por_estado ?? 0} por estado ya establecido). Escrituras físicas reales: ${resultado.optimizacion.escrituras_fisicas}.`
                        : "Optimización desactivada: se ejecutaron todas las escrituras."}
                    </p>
                  )}
                  {resultado.eventos.length === 0 && (
                    <p>No había instrucciones para ejecutar.</p>
                  )}
                  <ul className="eventos">
                    {resultado.eventos.map((evento, indice) => (
                      <li
                        key={indice}
                        className={
                          evento.estado === "OMITIDA" ? "evento-omitido" : ""
                        }
                      >
                        <span className="evento-linea">
                          Línea {evento.linea}
                        </span>
                        {evento.operacion === "ASIGNAR_ESTADO" &&
                        evento.dispositivo &&
                        evento.valor ? (
                          <DetalleEjecucion
                            evento={evento}
                            dispositivos={dispositivos}
                          />
                        ) : (
                          <>
                            <span className="evento-texto">
                              {evento.detalle}
                            </span>
                            <span className="evento-estado">
                              {evento.estado}
                            </span>
                          </>
                        )}
                        {evento.dispositivos && (
                          <details className="detalle-listado">
                            <summary>Ver lista de dispositivos</summary>
                            <ul>
                              {evento.dispositivos.map((d) => (
                                <li key={d.identificador}>
                                  {d.identificador}: {d.estado}
                                </li>
                              ))}
                            </ul>
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
                <p>
                  Últimas 30 operaciones registradas. Las asignaciones
                  optimizadas sin escritura física no aparecen aquí.
                </p>
              </div>
            </div>
            <div className="tabla-contenedor">
              <table>
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Instrucción</th>
                    <th>Resultado</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {historial.map((item) => (
                    <tr key={item.id}>
                      <td className="celda-fecha">{fechaCorta(item.fecha)}</td>
                      <td>
                        <code>{item.instruccion}</code>
                      </td>
                      <td
                        className={
                          item.estado_ejecucion === "ERROR"
                            ? "celda-resultado-error"
                            : undefined
                        }
                      >
                        {typeof item.resultado === "object" &&
                        item.resultado !== null
                          ? item.resultado.detalle
                          : (item.resultado ?? "—")}
                      </td>
                      <td className="celda-estado">
                        <span
                          className={
                            item.estado_ejecucion === "EXITOSA"
                              ? "texto-exito"
                              : item.estado_ejecucion === "ERROR"
                                ? "texto-error"
                                : "texto-tenue"
                          }
                        >
                          {item.estado_ejecucion}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {historial.length === 0 && (
                <p className="sin-registros">No hay operaciones registradas.</p>
              )}
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
                <p className="sin-registros">
                  No hay notificaciones registradas.
                </p>
              ) : (
                notificaciones.map((item) => (
                  <article key={item.id} className="notificacion">
                    <p>{item.mensaje}</p>
                    <time>{fechaCorta(item.fecha)}</time>
                  </article>
                ))
              )}
            </div>
          </section>
        </div>
        <footer className="pie">
          SmartHome · Simulación de dispositivos · React + FastAPI + PostgreSQL
        </footer>
      </main>
    </div>
  );
}
