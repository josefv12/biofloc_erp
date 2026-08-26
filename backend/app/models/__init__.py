# Biofloc ERP V1 - Models
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.models.auditoria import Auditoria
from app.models.estanque import EstadoEstanque, Estanque
from app.models.lote import Especie, EtapaProductiva, EstadoLote, Lote
from app.models.biometria import Biometria
from app.models.mortalidad import Mortalidad
from app.models.alimentacion import Alimentacion
from app.models.cosecha import Cosecha
from app.models.parametro_agua import ParametroAgua
from app.models.referencia_agua import ReferenciaAgua
from app.models.referencia_produccion import ReferenciaProduccion
from app.models.medicion_agua import MedicionAgua
from app.models.tipo_aplicacion_biofloc import TipoAplicacionBiofloc
from app.models.medicion_biofloc import MedicionBiofloc
from app.models.aplicacion_biofloc import AplicacionBiofloc
from app.models.referencia_biofloc import ReferenciaBiofloc
# Inventario CORE (Fase 6)
from app.models.categoria_inventario import CategoriaInventario
from app.models.unidad import Unidad
from app.models.producto import Producto
from app.models.tipo_movimiento_inventario import TipoMovimientoInventario
from app.models.movimiento_inventario import MovimientoInventario
# Compras (Fase 7)
from app.models.compra import Compra
from app.models.detalle_compra import DetalleCompra
# Finanzas (Fase 9): Gastos + Ventas
from app.models.categoria_gasto import CategoriaGasto
from app.models.gasto import Gasto
from app.models.venta import Venta, DetalleVenta
# Equipos + Mantenimientos + Fallas + Energía (Fase 10)
from app.models.equipo import TipoEquipo, EstadoEquipo, Equipo
from app.models.mantenimiento import TipoMantenimiento, Mantenimiento
from app.models.falla import Falla
from app.models.evento_energia import EventoEnergia
# Sistema general de alarmas (Fase 11)
from app.models.alarma import TipoAlarma, NivelAlarma, EstadoAlarma, Alarma
__all__ = [
    "Rol", "Usuario", "Auditoria",
    "EstadoEstanque", "Estanque",
    "Especie", "EtapaProductiva", "EstadoLote", "Lote",
    "Biometria", "Mortalidad", "Alimentacion", "Cosecha",
    "ParametroAgua", "ReferenciaAgua", "ReferenciaProduccion", "MedicionAgua",
    "TipoAplicacionBiofloc", "MedicionBiofloc", "AplicacionBiofloc", "ReferenciaBiofloc",
    # Inventario
    "CategoriaInventario", "Unidad", "Producto",
    "TipoMovimientoInventario", "MovimientoInventario",
    # Compras
    "Compra", "DetalleCompra",
    # Finanzas
    "CategoriaGasto", "Gasto", "Venta", "DetalleVenta",
    # Equipos / Mantenimientos / Fallas / Energía
    "TipoEquipo", "EstadoEquipo", "Equipo",
    "TipoMantenimiento", "Mantenimiento",
    "Falla", "EventoEnergia",
    # Alarmas generales
    "TipoAlarma", "NivelAlarma", "EstadoAlarma", "Alarma",
]
