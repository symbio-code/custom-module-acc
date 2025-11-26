from sqlmodel import Session, select
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.models.account import Account


ALLOWED_ACCOUNT_TYPES = {"asset", "liability", "equity", "revenue", "expense"}


def _validate_code(code: str):
    if not code:
        raise HTTPException(status_code=400, detail="Account code is required")
    code = str(code).strip()
    if not code.isdigit():
        raise HTTPException(status_code=400, detail="Account code must be numeric only")
    if len(code) > 7:
        raise HTTPException(status_code=400, detail="Account code must be at most 7 digits")
    return code


def _validate_account_type(account_type: str):
    if account_type not in ALLOWED_ACCOUNT_TYPES:
        raise HTTPException(status_code=400, detail=f"account_type must be one of {sorted(ALLOWED_ACCOUNT_TYPES)}")
    return account_type


def create_account(db: Session, data: Account):
    # Normalize and validate
    data.code = _validate_code(data.code)
    data.name = (data.name or "").strip()
    if not data.name:
        raise HTTPException(status_code=400, detail="Account name is required")
    data.account_type = _validate_account_type(data.account_type)

    # Parent resolution: if parent_code provided, ensure exists and is prefix
    parent = None
    if data.parent_code:
        parent_code = str(data.parent_code).strip()
        parent = db.exec(select(Account).where(Account.code == parent_code)).first()
        if not parent:
            raise HTTPException(status_code=400, detail="parent_code not found")
        if not data.code.startswith(parent.code):
            raise HTTPException(status_code=400, detail="Child code must start with parent_code")
        # set level based on parent
        data.level = (parent.level or 0) + 1
        # ensure parent is group
        if not parent.is_group:
            parent.is_group = True
            db.add(parent)
            db.commit()
            db.refresh(parent)
    else:
        # try to auto-detect parent by longest prefix match
        code = data.code
        possible_parent = None
        # iterate over existing accounts to find longest prefix match
        rows = db.exec(select(Account)).all()
        for r in rows:
            if code.startswith(r.code) and (possible_parent is None or len(r.code) > len(possible_parent.code)):
                possible_parent = r
        if possible_parent:
            data.parent_code = possible_parent.code
            data.level = (possible_parent.level or 0) + 1
            if not possible_parent.is_group:
                possible_parent.is_group = True
                db.add(possible_parent)
                db.commit()
                db.refresh(possible_parent)
        else:
            # top-level
            data.level = data.level or 0

    try:
        db.add(data)
        db.commit()
        db.refresh(data)
        return data
    except IntegrityError as e:
        db.rollback()
        # likely duplicate code
        raise HTTPException(status_code=400, detail="Account code already exists")

def get_account(db: Session, id: int):
    return db.get(Account, id)

def update_account(db: Session, id: int, payload: dict):
    acc = db.get(Account, id)
    if not acc:
        return None

    # Do not allow changing code via update to avoid hierarchy inconsistency
    if "code" in payload and str(payload.get("code")).strip() != acc.code:
        raise HTTPException(status_code=400, detail="Changing account code is not supported")

    if "account_type" in payload:
        payload["account_type"] = _validate_account_type(payload["account_type"])

    for k, v in payload.items():
        if k == "code":
            continue
        setattr(acc, k, v)

    try:
        db.add(acc)
        db.commit()
        db.refresh(acc)
        return acc
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to update account due to integrity error")

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
    allowed_sort = {"code", "name", "level", "account_type"}
    if sort_by not in allowed_sort:
        sort_by = "code"
    order_col = getattr(Account, sort_by)
    if sort_dir == "desc":
        order_col = order_col.desc()
    query = query.order_by(order_col)

    # PAGINATION ------------------------------
    # efficient count
    total_count_row = db.exec(select(func.count()).select_from(Account)).one()
    try:
        total_count = int(total_count_row[0])
    except Exception:
        total_count = 0

    offset = max(0, (page - 1)) * page_size
    rows = db.exec(query.offset(offset).limit(page_size)).all()

    return {
        "rows": rows,
        "total": total_count,
        "page": page,
        "page_size": page_size
    }