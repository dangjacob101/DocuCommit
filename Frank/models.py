from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def now_utc():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    hashed_password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=now_utc)

    documents = db.relationship("Document", back_populates="owner", cascade="all, delete-orphan")


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    created_at = db.Column(db.DateTime, default=now_utc)

    owner = db.relationship("User", back_populates="documents")
    branches = db.relationship(
        "Branch", back_populates="document", cascade="all, delete-orphan"
    )


class Branch(db.Model):
    __tablename__ = "branches"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    is_main = db.Column(db.Boolean, default=False, nullable=False)
    branched_from_commit_id = db.Column(
        db.Integer, db.ForeignKey("commits.id", ondelete="SET NULL"), nullable=True
    )
    status = db.Column(db.String(20), default="active", nullable=False)
    created_at = db.Column(db.DateTime, default=now_utc)

    document = db.relationship("Document", back_populates="branches")
    branched_from_commit = db.relationship(
        "Commit", foreign_keys=[branched_from_commit_id]
    )
    commits = db.relationship(
        "Commit",
        back_populates="branch",
        foreign_keys="Commit.branch_id",
        order_by="Commit.id",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint("document_id", "name"),
        db.Index("ix_branches_document_main", "document_id", "is_main"),
        db.Index("ix_branches_document_id", "document_id", "id"),
    )


class Commit(db.Model):
    __tablename__ = "commits"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    diff_patch = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=now_utc)

    branch = db.relationship(
        "Branch", back_populates="commits", foreign_keys=[branch_id]
    )

    __table_args__ = (db.Index("ix_commits_branch_id", "branch_id", "id"),)


def create_missing_indexes():
    for table in (Branch.__table__, Commit.__table__):
        for index in table.indexes:
            index.create(bind=db.engine, checkfirst=True)
