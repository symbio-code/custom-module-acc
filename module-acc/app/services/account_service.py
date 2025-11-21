from sqlmodel import Session, select
from app.models.account import Account

def create_account(db: Session, data: Account):
    db.add(data)
    db.commit()
    db.refresh(data)
    return data

def get_account(db: Session, id: int):
    return db.get(Account, id)

def update_account(db: Session, id: int, payload: dict):
    acc = db.get(Account, id)
    if not acc:
        return None
    
    for k, v in payload.items():
        setattr(acc, k, v)
    
    db.commit()
    db.refresh(acc)
    return acc

def delete_account(db: Session, id: int):
    acc = db.get(Account, id)
    if not acc:
        return False
    
    db.delete(acc)
    db.commit()
    return True

# ----------------------------
# Pagination + Sorting + Filter
# ----------------------------

def list_accounts(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    search: str = "",
    sort_by: str = "code",
    sort_dir: str = "asc"
):
    query = select(Account)

    # FILTER ---------------------------------
    if search:
        query = query.where(
            Account.name.ilike(f"%{search}%") |
            Account.code.ilike(f"%{search}%")
        )

    # SORT -----------------------------------
    order = getattr(Account, sort_by)
    if sort_dir == "desc":
        order = order.desc()
    query = query.order_by(order)

    # PAGINATION ------------------------------
    total = db.exec(select(Account)).all()
    total_count = len(total)

    offset = (page - 1) * page_size
    rows = db.exec(query.offset(offset).limit(page_size)).all()

    return {
        "rows": rows,
        "total": total_count,
        "page": page,
        "page_size": page_size
    }