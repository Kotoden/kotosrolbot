from __future__ import annotations
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id: int = Column(Integer, unique=True, nullable=False)
    username: Optional[str] = Column(String, nullable=True)
    full_name: Optional[str] = Column(String, nullable=True)
    is_admin: bool = Column(Boolean, default=False, nullable=False)
    orders: List[Order] = relationship("Order", back_populates="user", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String, unique=True, nullable=False)
    products: List[Product] = relationship("Product", back_populates="category", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String, nullable=False)
    description: Optional[str] = Column(String, nullable=True)
    price: float = Column(Float, nullable=False)
    quantity: int = Column(Integer, nullable=False, default=0)
    category_id: int = Column(Integer, ForeignKey("categories.id"), nullable=False)
    category: Category = relationship("Category", back_populates="products")
    order_items: List[OrderItem] = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    status: str = Column(String, nullable=False, default="pending")
    user: User = relationship("User", back_populates="orders")
    items: List[OrderItem] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    order_id: int = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id: int = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity: int = Column(Integer, nullable=False)
    unit_price: float = Column(Float, nullable=False)
    order: Order = relationship("Order", back_populates="items")
    product: Product = relationship("Product", back_populates="order_items")
