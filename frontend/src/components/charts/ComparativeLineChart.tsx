import { useId, useMemo, type ReactElement } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatNumber } from "../../utils/format";
import type { PuntoComparativo } from "../../utils/series";
import { COLORES_COMPARATIVA } from "../../utils/comparativeColors";

/** Colores fijos para series de referencia (convención visual del ERP). */
export { COLORES_COMPARATIVA };

type SerieComparativa = {
  key: keyof PuntoComparativo | "real";
  nombre: string;
  color: string;
  referencia: boolean;
};

const SERIES_REFERENCIA: Omit<SerieComparativa, "color">[] = [
  { key: "maximo", nombre: "Máximo", referencia: true },
  { key: "minimo", nombre: "Mínimo", referencia: true },
  { key: "objetivo", nombre: "Objetivo", referencia: true },
  { key: "esperado", nombre: "Esperado", referencia: true },
  { key: "recomendado", nombre: "Recomendada", referencia: true },
];

const TICK = { fontSize: 11, fill: "var(--bf-muted)", fontFamily: "IBM Plex Sans, sans-serif" };

function colorReferencia(key: string): string {
  switch (key) {
    case "maximo":
      return COLORES_COMPARATIVA.maximo;
    case "minimo":
      return COLORES_COMPARATIVA.minimo;
    case "objetivo":
      return COLORES_COMPARATIVA.objetivo;
    case "esperado":
      return COLORES_COMPARATIVA.esperado;
    case "recomendado":
      return COLORES_COMPARATIVA.recomendada;
    default:
      return COLORES_COMPARATIVA.objetivo;
  }
}

function serieTieneDatos(data: PuntoComparativo[], key: string): boolean {
  return data.some((punto) => {
    const valor = punto[key as keyof PuntoComparativo];
    return typeof valor === "number" && Number.isFinite(valor);
  });
}

function calcularDominioY(data: PuntoComparativo[], keys: string[]): [number, number] {
  const valores: number[] = [];
  for (const punto of data) {
    for (const key of keys) {
      const valor = punto[key as keyof PuntoComparativo];
      if (typeof valor === "number" && Number.isFinite(valor)) {
        valores.push(valor);
      }
    }
  }
  if (valores.length === 0) {
    return [0, 1];
  }
  const min = Math.min(...valores);
  const max = Math.max(...valores);
  const rango = max - min;
  const padding = rango > 0 ? rango * 0.12 : Math.max(Math.abs(max) * 0.1, 1);
  return [min - padding, max + padding];
}

type ComparativeLineChartProps = {
  data: PuntoComparativo[];
  unidad?: string | null;
  /** Color de la línea Real (verde/rojo/amarillo según evaluación). */
  colorReal?: string;
  digitos?: number;
  altura?: number;
  /** Banda sutil entre mínimo y máximo cuando ambos existen. */
  mostrarBandaRango?: boolean;
};

function formatearValor(valor: unknown, unidad: string | null | undefined, digitos: number): string {
  if (valor === null || valor === undefined || typeof valor !== "number" || !Number.isFinite(valor)) {
    return "N/D";
  }
  const texto = formatNumber(valor, { maximumFractionDigits: digitos });
  return unidad ? `${texto} ${unidad}` : texto;
}

function colorPuntoReal(punto: PuntoComparativo, fallback: string): string {
  const { real, minimo, maximo } = punto;
  if (real == null || !Number.isFinite(real)) return fallback;
  if (minimo == null && maximo == null) return fallback;
  if (minimo != null && real < minimo) return COLORES_COMPARATIVA.realFuera;
  if (maximo != null && real > maximo) return COLORES_COMPARATIVA.realFuera;
  return COLORES_COMPARATIVA.realOk;
}

function colorCss(color: string): string {
  return color.startsWith("var(") ? "#1f6b54" : color;
}

function PuntoReal(props: {
  cx?: number;
  cy?: number;
  payload?: PuntoComparativo;
  colorReal: string;
  activo?: boolean;
}): ReactElement | null {
  const { cx, cy, payload, colorReal, activo } = props;
  if (cx == null || cy == null || !payload) return <g />;
  const fill = colorPuntoReal(payload, colorReal);
  if (activo) {
    return (
      <g>
        <circle cx={cx} cy={cy} r={9} fill={fill} opacity={0.18} />
        <circle cx={cx} cy={cy} r={5.5} fill={fill} stroke="#fff" strokeWidth={2} />
      </g>
    );
  }
  return <circle cx={cx} cy={cy} r={4.5} fill={fill} stroke="#fff" strokeWidth={2} />;
}

/** Gráfica comparativa genérica: Real vs referencia/esperado/recomendado. */
export function ComparativeLineChart({
  data,
  unidad,
  colorReal = COLORES_COMPARATIVA.realNeutral,
  digitos = 3,
  altura = 300,
  mostrarBandaRango = true,
}: ComparativeLineChartProps) {
  const gradId = `bf-real-${useId().replace(/:/g, "")}`;
  const series = useMemo(() => {
    const lista: SerieComparativa[] = [];
    for (const ref of SERIES_REFERENCIA) {
      if (serieTieneDatos(data, ref.key)) {
        lista.push({ ...ref, color: colorReferencia(ref.key) });
      }
    }
    if (serieTieneDatos(data, "real")) {
      lista.push({ key: "real", nombre: "Real", color: colorReal, referencia: false });
    }
    return lista;
  }, [data, colorReal]);

  const keysActivas = useMemo(() => series.map((s) => s.key as string), [series]);
  const dominioY = useMemo(() => calcularDominioY(data, keysActivas), [data, keysActivas]);
  const hayReal = series.some((serie) => serie.key === "real");

  const banda = useMemo(() => {
    if (!mostrarBandaRango || data.length === 0) return null;
    const min = data[0]?.minimo;
    const max = data[0]?.maximo;
    if (min == null || max == null || !Number.isFinite(min) || !Number.isFinite(max)) return null;
    if (!data.every((p) => p.minimo === min && p.maximo === max)) return null;
    return { min, max };
  }, [data, mostrarBandaRango]);

  if (data.length === 0) {
    return null;
  }

  return (
    <div style={{ height: altura }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 28, right: 12, bottom: 4, left: 0 }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={colorCss(colorReal)} stopOpacity={0.22} />
              <stop offset="100%" stopColor={colorCss(colorReal)} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--bf-border)" strokeOpacity={0.55} strokeDasharray="4 8" vertical={false} />
          <XAxis
            dataKey="etiqueta"
            tick={TICK}
            minTickGap={24}
            interval="preserveStartEnd"
            axisLine={false}
            tickLine={false}
            tickMargin={8}
          />
          <YAxis
            domain={dominioY}
            tick={TICK}
            width={52}
            axisLine={false}
            tickLine={false}
            tickMargin={6}
            tickFormatter={(valor) => formatNumber(valor, { maximumFractionDigits: digitos })}
          />
          <Tooltip
            cursor={{ stroke: "var(--bf-border)", strokeDasharray: "3 3" }}
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              const orden = ["maximo", "minimo", "objetivo", "esperado", "recomendado", "real"];
              const filas = [...payload]
                .filter((item) => item.dataKey !== "realArea")
                .sort((a, b) => orden.indexOf(String(a.dataKey)) - orden.indexOf(String(b.dataKey)));
              return (
                <div className="rounded-xl border border-[var(--bf-border)] bg-white/95 px-3 py-2.5 shadow-[0_8px_24px_rgba(16,40,33,0.12)] backdrop-blur-sm">
                  <p className="mb-2 text-[11px] font-semibold text-[var(--bf-ink)]">{label}</p>
                  <ul className="space-y-1 text-xs">
                    {filas.map((item) => {
                      const serie = series.find((s) => s.key === item.dataKey);
                      if (!serie) return null;
                      return (
                        <li key={String(item.dataKey)} className="flex items-center gap-2">
                          <span
                            className="inline-block h-[3px] w-4 shrink-0 rounded-full"
                            style={{ backgroundColor: serie.color }}
                          />
                          <span className="text-[var(--bf-muted)]">{serie.nombre}:</span>
                          <span className="font-semibold tabular-nums text-[var(--bf-ink)]">
                            {formatearValor(item.value, unidad, digitos)}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            }}
          />
          <Legend
            verticalAlign="top"
            align="left"
            iconSize={16}
            wrapperStyle={{ fontSize: 11, paddingBottom: 6, lineHeight: "18px", color: "var(--bf-muted)" }}
            formatter={(value) => <span className="text-[11px] text-[var(--bf-muted)]">{value}</span>}
          />
          {banda ? (
            <ReferenceArea
              y1={banda.min}
              y2={banda.max}
              fill="var(--bf-accent)"
              fillOpacity={0.07}
              strokeOpacity={0}
            />
          ) : null}
          {hayReal ? (
            <Area
              type="linear"
              dataKey="real"
              name="realArea"
              stroke="none"
              fill={`url(#${gradId})`}
              legendType="none"
              isAnimationActive={false}
            />
          ) : null}
          {series.map((serie) => (
            <Line
              key={serie.key}
              type="linear"
              dataKey={serie.key}
              name={serie.nombre}
              stroke={serie.referencia ? serie.color : COLORES_COMPARATIVA.realNeutral}
              strokeWidth={serie.referencia ? 1.75 : 2.75}
              strokeDasharray={serie.referencia ? "5 4" : undefined}
              strokeLinecap="round"
              strokeLinejoin="round"
              dot={
                serie.referencia
                  ? false
                  : (props) => (
                      <PuntoReal
                        cx={props.cx}
                        cy={props.cy}
                        payload={props.payload as PuntoComparativo}
                        colorReal={colorReal}
                      />
                    )
              }
              activeDot={
                serie.referencia
                  ? false
                  : (props) => (
                      <PuntoReal
                        cx={props.cx}
                        cy={props.cy}
                        payload={props.payload as PuntoComparativo}
                        colorReal={colorReal}
                        activo
                      />
                    )
              }
              connectNulls={serie.referencia}
              isAnimationActive={false}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
