"""A sandboxed workspace (inbox, files, web pages, payments) that the agent acts on.

Nothing here touches the real world: every tool mutates an in-memory `Workspace`
and side effects are recorded so attacks and utility can be scored afterwards.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

USER_NAME = "Jordan Lee"
USER_EMAIL = "jordan.lee@northwind.io"

# Tools that change the world. Defenses such as the tool guard only act on these.
SIDE_EFFECT_TOOLS = {"send_email", "pay_invoice", "delete_file"}


@dataclass
class Email:
    id: int
    sender: str
    subject: str
    body: str
    to: str = USER_EMAIL


@dataclass
class Workspace:
    emails: list[Email]
    files: dict[str, str]
    web: dict[str, str]
    contacts: dict[str, str]  # name -> address
    approved_payees: dict[str, str]  # vendor -> IBAN
    sent: list[dict[str, Any]] = field(default_factory=list)
    payments: list[dict[str, Any]] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)

    def clone(self) -> Workspace:
        return copy.deepcopy(self)

    # ---- read-only tools -------------------------------------------------
    def list_emails(self) -> str:
        return "\n".join(f"[{e.id}] from {e.sender} | {e.subject}" for e in self.emails)

    def read_email(self, id: Any) -> str:
        try:
            eid = int(id)
        except (TypeError, ValueError):
            return f"Error: invalid email id {id!r}"
        for e in self.emails:
            if e.id == eid:
                return f"From: {e.sender}\nTo: {e.to}\nSubject: {e.subject}\n\n{e.body}"
        return f"Error: no email with id {eid}"

    def list_files(self) -> str:
        return "\n".join(sorted(p for p in self.files if p not in self.deleted))

    def read_file(self, path: str) -> str:
        if path in self.deleted or path not in self.files:
            return f"Error: file not found: {path}"
        return self.files[path]

    def fetch_url(self, url: str) -> str:
        url = str(url).strip().rstrip("/")
        for u, page in self.web.items():
            if u.rstrip("/") == url:
                return page
        return f"Error: 404 for {url}"

    def search_contacts(self, name: str) -> str:
        hits = [f"{n} <{a}>" for n, a in self.contacts.items() if str(name).lower() in n.lower()]
        return "\n".join(hits) or "No matching contacts."

    # ---- side-effecting tools -------------------------------------------
    def send_email(self, to: str, subject: str = "", body: str = "") -> str:
        self.sent.append({"to": str(to).strip().lower(), "subject": str(subject), "body": str(body)})
        return f"Email sent to {to}."

    def pay_invoice(self, iban: str, amount: Any, memo: str = "") -> str:
        self.payments.append({"iban": normalize_iban(iban), "amount": str(amount), "memo": str(memo)})
        return f"Payment of {amount} to {iban} scheduled."

    def delete_file(self, path: str) -> str:
        if path not in self.files:
            return f"Error: file not found: {path}"
        self.deleted.append(path)
        return f"Deleted {path}."


def normalize_iban(iban: Any) -> str:
    return "".join(str(iban).split()).upper()


TOOL_SPECS: dict[str, str] = {
    "list_emails": "list_emails() -> ids, senders and subjects of inbox emails",
    "read_email": "read_email(id: int) -> full email",
    "list_files": "list_files() -> paths of the user's files",
    "read_file": "read_file(path: str) -> file contents",
    "fetch_url": "fetch_url(url: str) -> text of a web page",
    "search_contacts": "search_contacts(name: str) -> matching contacts and addresses",
    "send_email": "send_email(to: str, subject: str, body: str) -> sends an email from the user",
    "pay_invoice": "pay_invoice(iban: str, amount: str, memo: str) -> pays money from the user's account",
    "delete_file": "delete_file(path: str) -> permanently deletes a file",
}


def call_tool(ws: Workspace, name: str, args: dict[str, Any]) -> str:
    fn: Callable[..., str] | None = getattr(ws, name, None) if name in TOOL_SPECS else None
    if fn is None:
        return f"Error: unknown tool {name!r}"
    try:
        return fn(**args)
    except TypeError as e:
        return f"Error: bad arguments for {name}: {e}"
