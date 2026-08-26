import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatChartValue, formatNumber } from "../../utils/format";
import type { PuntoSerie } from "../../utils/series";

export type SerieDefinicion = {
  key: string;
  nombre: string;
  color?: string;
  /** Líneas de referencia: trazo discontinuo, sin puntos. */
  referencia?: boolean;
};

export type LineaReferencia = {
  valor: number;
  etiqueta: string;
  color?: string;
};

type TimeSeriesChartProps = {
  data: PuntoSerie[];
  series: SerieDefinicion[];
  unidad?: string | null;
  /** @deprecated Preferir series con referencia repetida en cada punto. */
  referencias?: LineaReferencia[];
  digitos?: number;
  altura?: number;
};

const COLORES = ["var(--bf-accent)", "#1c4f43", "#b45309"];
const TICK = { fontSize: 11, fill: "var(--bf-muted)", fontFamily: "IBM Plex Sans, sans-serif" };

/** Serie temporal: el eje X usa fechas ya formateadas en America/Bogota. */
export function TimeSeriesChart({
  data,
  series,
  unidad,
  referencias = [],
  digitos = 3,
  altura = 280,
}: TimeSeriesChartProps) {
  return (
    <div style={{ height: altura }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 12, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="var(--bf-border)" strokeOpacity={0.55} strokeDasharray="4 8" vertical={false} />
          <XAxis dataKey="etiqueta" tick={TICK} minTickGap={16} axisLine={false} tickLine={false} tickMargin={8} />
          <YAxis
            tick={TICK}
            width={56}
            axisLine={false}
            tickLine={false}
            tickMargin={6}
            tickFormatter={(valor) => formatNumber(valor, { maximumFractionDigits: digitos })}
          />
          <Tooltip
            cursor={{ stroke: "var(--bf-border)", strokeDasharray: "3 3" }}
            contentStyle={{
              borderRadius: 12,
              border: "1px solid var(--bf-border)",
              boxShadow: "0 8px 24px rgba(16,40,33,0.12)",
              fontSize: 12,
            }}
            formatter={(valor, nombre) => [
              formatChartValue(valor, { maximumFractionDigits: digitos }, unidad),
              nombre,
            ]}
          />
          {series.length > 1 || referencias.length > 0 ? (
            <Legend wrapperStyle={{ fontSize: 11, color: "var(--bf-muted)" }} />
          ) : null}
          {referencias.map((referencia) => (
            <ReferenceLine
              key={referencia.etiqueta}
              y={referencia.valor}
              stroke={referencia.color ?? "#b45309"}
              strokeDasharray="5 4"
              label={{ value: referencia.etiqueta, position: "insideTopRight", fontSize: 10 }}
            />
          ))}
          {series.map((serie, index) => (
            <Line
              key={serie.key}
              type="monotone"
              dataKey={serie.key}
              name={serie.nombre}
              stroke={serie.color ?? COLORES[index % COLORES.length]}
              strokeWidth={serie.referencia ? 1.75 : 2.5}
              strokeDasharray={serie.referencia ? "5 4" : undefined}
              strokeLinecap="round"
              dot={serie.referencia ? false : { r: 4, stroke: "#fff", strokeWidth: 2 }}
              activeDot={serie.referencia ? false : { r: 6, stroke: "#fff", strokeWidth: 2 }}
              connectNulls={serie.referencia ? true : false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
