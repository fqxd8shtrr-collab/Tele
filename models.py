from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json
from config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    phone = Column(String, unique=True)
    session_name = Column(String)
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    channels = relationship("Channel", back_populates="account")
    posts = relationship("Post", back_populates="account")

class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    title = Column(String)
    username = Column(String, nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    is_monitored = Column(Boolean, default=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    account = relationship("Account", back_populates="channels")
    posts = relationship("Post", back_populates="channel")

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer)
    channel_id = Column(Integer, ForeignKey("channels.id"))
    account_id = Column(Integer, ForeignKey("accounts.id"))
    source_username = Column(String, nullable=True)
    text = Column(Text, nullable=True)
    translated_text = Column(Text, nullable=True)
    media_type = Column(String, default="none")
    media_group_id = Column(String, nullable=True)
    ai_importance = Column(Float, default=0.0)
    ai_category = Column(String, nullable=True)
    is_urgent = Column(Boolean, default=False)
    is_duplicate = Column(Boolean, default=False)
    duplicate_group = Column(String, nullable=True)
    hot_event_id = Column(String, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    channel = relationship("Channel", back_populates="posts")
    account = relationship("Account", back_populates="posts")

class Destination(Base):
    __tablename__ = "destinations"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    type = Column(String)   # channel, group, private
    identifier = Column(String)
    is_active = Column(Boolean, default=True)
    send_method = Column(String, default="forward")  # forward, copy, text_only
    rules = Column(Text, default="{}")

    def get_rules(self):
        return json.loads(self.rules)

    def set_rules(self, rules_dict):
        self.rules = json.dumps(rules_dict)

class Keyword(Base):
    __tablename__ = "keywords"
    id = Column(Integer, primary_key=True)
    text = Column(String)
    language = Column(String, default="ar")
    priority = Column(Integer, default=1)
    is_include = Column(Boolean, default=True)

Base.metadata.create_all(engine)
