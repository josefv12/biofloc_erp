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
  referencias?: LineaReferencia[];
  digitos?: number;
  altura?: number;
};

const COLORES = ["var(--bf-accent)", "#1c4f43", "#b45309"];

/** Serie temporal: el eje X usa fechas ya formateadas en America/Bogota. */
export function TimeSeriesChart({
  data,
  series,
  unidad,
  referencias = [],
  digitos = 3,
  altura = 240,
}: TimeSeriesChartProps) {
  return (
    <div style={{ height: altura }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--bf-border)" vertical={false} />
          <XAxis dataKey="etiqueta" tick={{ fontSize: 11 }} minTickGap={16} />
          <YAxis
            tick={{ fontSize: 11 }}
            width={56}
            tickFormatter={(valor) => formatNumber(valor, { maximumFractionDigits: digitos })}
          />
          <Tooltip
            formatter={(valor, nombre) => [
              formatChartValue(valor, { maximumFractionDigits: digitos }, unidad),
              nombre,
            ]}
          />
          {series.length > 1 || referencias.length > 0 ? <Legend wrapperStyle={{ fontSize: 11 }} /> : null}
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
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
