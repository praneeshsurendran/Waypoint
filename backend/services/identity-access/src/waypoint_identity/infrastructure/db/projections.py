from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base


class Depot(Base):
    __tablename__ = "network_depots"
    code: Mapped[str] = mapped_column(String(50), primary_key=True)


class Outlet(Base):
    __tablename__ = "network_outlets"
    outlet_id: Mapped[str] = mapped_column(String(20), primary_key=True)


class Vehicle(Base):
    __tablename__ = "network_vehicles"
    vehicle_id: Mapped[str] = mapped_column(String(20), primary_key=True)


class Trip(Base):
    __tablename__ = "delivery_trips"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_id: Mapped[str] = mapped_column(String(20))
    trip_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
