from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey,
    Text,
    BigInteger,
)

Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    language = Column(Text, nullable=True)

    calculations = relationship("Calculation", back_populates="user")

    def to_dict(self):
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "language": self.language,
        }


class Project(Base):
    __tablename__ = "project"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    category = Column(String(100), nullable=True)
    coin_name = Column(String(100), nullable=True)

    calculations = relationship("Calculation", back_populates="project")
    basic_metrics = relationship("BasicMetrics", back_populates="project")
    investing_metrics = relationship(
        "InvestingMetrics", back_populates="project"
    )
    social_metrics = relationship("SocialMetrics", back_populates="project")
    tokenomics = relationship("Tokenomics", back_populates="project")
    funds_profit = relationship("FundsProfit", back_populates="project")
    top_and_bottom = relationship("TopAndBottom", back_populates="project")
    market_metrics = relationship("MarketMetrics", back_populates="project")
    manipulative_metrics = relationship(
        "ManipulativeMetrics", back_populates="project"
    )
    network_metrics = relationship("NetworkMetrics", back_populates="project")
    agentanswer = relationship("AgentAnswer", back_populates="project")

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "coin_name": self.coin_name,
        }


class Calculation(Base):
    __tablename__ = "calculation"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = Column(
        BigInteger, ForeignKey("user.telegram_id"), nullable=False
    )
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    date = Column(DateTime, nullable=True)
    agent_answer = Column(Text, nullable=True)

    user = relationship("User", back_populates="calculations")
    project = relationship("Project", back_populates="calculations")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "date": self.date.isoformat() if self.date else None,
            "agent_answer": self.agent_answer,
        }


class BasicMetrics(Base):
    __tablename__ = "basic_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    project_id = Column(
        Integer, ForeignKey("project.id"), nullable=False, unique=True
    )
    entry_price = Column(Float, nullable=True)
    sphere = Column(String(150), nullable=True)
    market_price = Column(Float, nullable=True)

    project = relationship("Project", back_populates="basic_metrics")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "entry_price": self.entry_price,
            "sphere": self.sphere,
            "market_price": self.market_price,
        }


class InvestingMetrics(Base):
    __tablename__ = "investing_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    project_id = Column(
        Integer, ForeignKey("project.id"), nullable=False, unique=True
    )
    fundraise = Column(Float, nullable=True)
    fund_level = Column(Text, nullable=True)

    project = relationship("Project", back_populates="investing_metrics")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "fundraise": self.fundraise,
            "fund_level": self.fund_level,
        }


class SocialMetrics(Base):
    __tablename__ = "social_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    project_id = Column(
        Integer, ForeignKey("project.id"), nullable=False, unique=True
    )
    twitter = Column(Text, nullable=True)
    twitterscore = Column(Integer, nullable=True)

    project = relationship("Project", back_populates="social_metrics")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "twitter": self.twitter,
            "twitterscore": self.twitterscore,
        }


class Tokenomics(Base):
    __tablename__ = "tokenomics"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    project_id = Column(
        Integer, ForeignKey("project.id"), nullable=False, unique=True
    )
    circ_supply = Column(Float, nullable=True)
    total_supply = Column(Float, nullable=True)
    capitalization = Column(Float, nullable=True)
    fdv = Column(Float, nullable=True)

    project = relationship("Project", back_populates="tokenomics")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "circ_supply": self.circ_supply,
            "total_supply": self.total_supply,
            "capitalization": self.capitalization,
            "fdv": self.fdv,
        }


class FundsProfit(Base):
    __tablename__ = "funds_profit"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    project_id = Column(
        Integer, ForeignKey("project.id"), nullable=False, unique=True
    )
    distribution = Column(Text, nullable=True)
    average_price = Column(Float, nullable=True)
    x_value = Column(Float, nullable=True)

    project = relationship("Project", back_populates="funds_profit")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "distribution": self.distribution,
            "average_price": self.average_price,
            "x_value": self.x_value,
        }


class TopAndBottom(Base):
    __tablename__ = "top_and_bottom"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    project_id = Column(
        Integer, ForeignKey("project.id"), nullable=False, unique=True
    )
    lower_threshold = Column(Float, nullable=True)
    upper_threshold = Column(Float, nullable=True)

    project = relationship("Project", back_populates="top_and_bottom")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "lower_threshold": self.lower_threshold,
            "upper_threshold": self.upper_threshold,
        }


class MarketMetrics(Base):
    __tablename__ = "market_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    project_id = Column(
        Integer, ForeignKey("project.id"), nullable=False, unique=True
    )
    fail_high = Column(Float, nullable=True)
    growth_low = Column(Float, nullable=True)

    project = relationship("Project", back_populates="market_metrics")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "fail_high": self.fail_high,
            "growth_low": self.growth_low,
        }


class ManipulativeMetrics(Base):
    __tablename__ = "manipulative_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    project_id = Column(
        Integer, ForeignKey("project.id"), nullable=False, unique=True
    )
    fdv_fundraise = Column(Float, nullable=True)
    top_100_wallet = Column(Float, nullable=True)

    project = relationship("Project", back_populates="manipulative_metrics")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "fdv_fundraise": self.fdv_fundraise,
            "top_100_wallet": self.top_100_wallet,
        }


class NetworkMetrics(Base):
    __tablename__ = "network_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    project_id = Column(
        Integer, ForeignKey("project.id"), nullable=False, unique=True
    )
    tvl = Column(Float, nullable=True)
    tvl_fdv = Column(Float, nullable=True)

    project = relationship("Project", back_populates="network_metrics")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "tvl": self.tvl,
            "tvl_fdv": self.tvl_fdv,
        }


class AgentAnswer(Base):
    __tablename__ = "agentanswer"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    answer = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="agentanswer")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "answer": self.answer,
            "language": self.language,
            "updated_at": self.updated_at.isoformat()
            if self.updated_at
            else None,
        }
