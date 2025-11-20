from sqlmodel import Session, select
from app.models import (
    User,
    Company,
    Account,
    AccountingPeriod,
    OpeningBalance,
    JournalEntry,
    JournalLine,
    GLEntry,
)
from datetime import datetime


# -----------------------------------------------------------
# USER SERVICE
# -----------------------------------------------------------

def create_user(db: Session, username: str, password_hash: str, role: str = "user"):
    user = User(username=username, password_hash=password_hash, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str):
    return db.exec(select(User).where(User.username == username)).first()


# -----------------------------------------------------------
# COMPANY SERVICE
# -----------------------------------------------------------

def create_company(db: Session, name: str, currency: str = "IDR"):
    company = Company(name=name, currency=currency)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def list_companies(db: Session):
    return db.exec(select(Company)).all()


# -----------------------------------------------------------
# ACCOUNT SERVICE
# -----------------------------------------------------------

def create_account(db: Session, code: str, name: str, account_type: str, parent_id=None):
    account = Account(code=code, name=name, account_type=account_type, parent_id=parent_id)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def list_accounts(db: Session):
    return db.exec(select(Account)).all()


# -----------------------------------------------------------
# ACCOUNTING PERIOD
# -----------------------------------------------------------

def create_period(db: Session, name: str, start_date, end_date):
    period = AccountingPeriod(
        period_name=name,
        start_date=start_date,
        end_date=end_date,
        is_closed=False
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


def close_period(db: Session, period_id: int):
    period = db.get(AccountingPeriod, period_id)
    if not period:
        return None
    period.is_closed = True
    db.add(period)
    db.commit()
    return period


# -----------------------------------------------------------
# OPENING BALANCE SERVICE
# -----------------------------------------------------------

def create_opening_balance(db: Session, account_id: int, debit: float = 0, credit: float = 0):
    ob = OpeningBalance(account_id=account_id, debit=debit, credit=credit)
    db.add(ob)
    db.commit()
    db.refresh(ob)
    return ob


def list_opening_balances(db: Session):
    return db.exec(select(OpeningBalance)).all()


# -----------------------------------------------------------
# JOURNAL ENTRY + JOURNAL LINES + GL POSTING
# -----------------------------------------------------------

def create_journal_entry(db: Session, date: datetime, reference: str = "", memo: str = ""):
    entry = JournalEntry(date=date, reference=reference, memo=memo, posted=False)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def add_journal_line(db: Session, journal_entry_id: int, account_id: int, debit=0, credit=0):
    line = JournalLine(
        journal_entry_id=journal_entry_id,
        account_id=account_id,
        debit=debit,
        credit=credit
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def post_journal_to_gl(db: Session, journal_entry_id: int):
    lines = db.exec(
        select(JournalLine).where(JournalLine.journal_entry_id == journal_entry_id)
    ).all()

    for line in lines:
        gl = GLEntry(
            journal_entry_id=journal_entry_id,
            account_id=line.account_id,
            debit=line.debit,
            credit=line.credit,
            balance_after=0  # nanti bisa dihitung
        )
        db.add(gl)

    entry = db.get(JournalEntry, journal_entry_id)
    entry.posted = True

    db.commit()
    return {"posted": True, "journal_entry_id": journal_entry_id}


# -----------------------------------------------------------
# GENERAL LEDGER & TRIAL BALANCE
# -----------------------------------------------------------

def get_general_ledger(db: Session, account_id: int):
    return db.exec(select(GLEntry).where(GLEntry.account_id == account_id)).all()


def get_trial_balance(db: Session):
    accounts = db.exec(select(Account)).all()
    output = []

    for acc in accounts:
        entries = db.exec(
            select(GLEntry).where(GLEntry.account_id == acc.id)
        ).all()

        debit = sum(e.debit for e in entries)
        credit = sum(e.credit for e in entries)

        output.append({
            "account": f"{acc.code} - {acc.name}",
            "debit": debit,
            "credit": credit,
            "balance": debit - credit
        })

    return output


# -----------------------------------------------------------
# BALANCE SHEET STYLE SUMMARY (SIMPLE)
# -----------------------------------------------------------

def get_simple_balance_sheet(db: Session):
    tb = get_trial_balance(db)

    total_assets = sum(x["balance"] for x in tb if x["balance"] > 0)
    total_liab_eq = -sum(x["balance"] for x in tb if x["balance"] < 0)

    return {
        "assets": total_assets,
        "liabilities_equity": total_liab_eq,
        "balanced": total_assets == total_liab_eq
    }
