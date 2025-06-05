from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from database.models import User, Category, Product, Order, OrderItem


def get_or_create_user(
        db: Session, telegram_id: int, username: Optional[str], full_name: Optional[str], is_admin: bool = False
) -> User:
    user = db.query(User).filter(User.telegram_id == telegram_id).one_or_none()
    if user:
        user.username = username
        user.full_name = full_name
        db.commit()
        db.refresh(user)
        return user
    new_user = User(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
        is_admin=is_admin,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def get_all_categories(db: Session) -> List[Category]:
    return db.query(Category).order_by(Category.name).all()


def create_category(db: Session, name: str) -> Category:
    existing = db.query(Category).filter(Category.name == name).one_or_none()
    if existing:
        raise ValueError(f"Category '{name}' already exists.")
    category = Category(name=name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def get_products(
        db: Session, category_id: Optional[int] = None
) -> List[Product]:
    query = db.query(Product)
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    return query.order_by(Product.name).all()


def create_product(
        db: Session,
        name: str,
        description: str,
        price: float,
        quantity: int,
        category_id: int,
) -> Product:
    cat = db.query(Category).filter(Category.id == category_id).one_or_none()
    if not cat:
        raise ValueError(f"Category id={category_id} not found.")
    product = Product(
        name=name,
        description=description,
        price=price,
        quantity=quantity,
        category_id=category_id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(
        db: Session,
        product_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[float] = None,
        quantity: Optional[int] = None,
        category_id: Optional[int] = None,
) -> Product:
    product = db.query(Product).filter(Product.id == product_id).one_or_none()
    if not product:
        raise NoResultFound(f"Product id={product_id} not found.")
    if name is not None:
        product.name = name
    if description is not None:
        product.description = description
    if price is not None:
        product.price = price
    if quantity is not None:
        product.quantity = quantity
    if category_id is not None:
        cat = db.query(Category).filter(Category.id == category_id).one_or_none()
        if not cat:
            raise ValueError(f"Category id={category_id} not found.")
        product.category_id = category_id
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> None:
    product = db.query(Product).filter(Product.id == product_id).one_or_none()
    if not product:
        raise NoResultFound(f"Product id={product_id} not found.")
    db.delete(product)
    db.commit()


def create_order(db: Session, user_id: int) -> Order:
    user = db.query(User).filter(User.id == user_id).one_or_none()
    if not user:
        raise NoResultFound(f"User id={user_id} not found.")
    order = Order(user_id=user_id, status="pending", created_at=datetime.utcnow())
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def add_item_to_order(
        db: Session, order_id: int, product_id: int, quantity: int
) -> OrderItem:
    order = db.query(Order).filter(Order.id == order_id).one_or_none()
    if not order:
        raise NoResultFound(f"Order id={order_id} not found.")
    product = db.query(Product).filter(Product.id == product_id).one_or_none()
    if not product:
        raise NoResultFound(f"Product id={product_id} not found.")
    if product.quantity < quantity:
        raise ValueError(f"Insufficient stock for product id={product_id}.")
    unit_price = product.price
    product.quantity -= quantity
    item = OrderItem(
        order_id=order_id,
        product_id=product_id,
        quantity=quantity,
        unit_price=unit_price,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_orders_by_user(db: Session, user_id: int) -> List[Order]:
    return (
        db.query(Order)
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .all()
    )


def get_order_details(db: Session, order_id: int) -> Tuple[Order, float]:
    order = db.query(Order).filter(Order.id == order_id).one_or_none()
    if not order:
        raise NoResultFound(f"Order id={order_id} not found.")
    total_price = sum(item.quantity * item.unit_price for item in order.items)
    return order, total_price


def update_order_status(db: Session, order_id: int, new_status: str) -> Order:
    order = db.query(Order).filter(Order.id == order_id).one_or_none()
    if not order:
        raise NoResultFound(f"Order id={order_id} not found.")
    order.status = new_status
    db.commit()
    db.refresh(order)
    return order
