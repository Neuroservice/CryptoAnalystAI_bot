from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, nullable=False)
    telegram_id = Column(Integer, nullable=False)
    language = Column(Text, nullable=True)

    calculations = relationship('Calculation', back_populates='user')


class Project(Base):
    __tablename__ = 'project'

    id = Column(Integer, primary_key=True, nullable=False)
    category = Column(String(100), nullable=True)
    coin_name = Column(String(100), nullable=True)

    calculations = relationship('Calculation', back_populates='project')
    basic_metrics = relationship('BasicMetrics', back_populates='project')
    investing_metrics = relationship('InvestingMetrics', back_populates='project')
    social_metrics = relationship('SocialMetrics', back_populates='project')
    tokenomics = relationship('Tokenomics', back_populates='project')
    funds_profit = relationship('FundsProfit', back_populates='project')
    top_and_bottom = relationship('TopAndBottom', back_populates='project')
    market_metrics = relationship('MarketMetrics', back_populates='project')
    manipulative_metrics = relationship('ManipulativeMetrics', back_populates='project')
    network_metrics = relationship('NetworkMetrics', back_populates='project')
    agentanswer = relationship('AgentAnswer', back_populates='project')


class Calculation(Base):
    __tablename__ = 'calculation'

    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    date = Column(DateTime, nullable=True)
    agent_answer = Column(Text, nullable=True)

    user = relationship('User', back_populates='calculations')
    project = relationship('Project', back_populates='calculations')


class BasicMetrics(Base):
    __tablename__ = 'basic_metrics'

    id = Column(Integer, primary_key=True, nullable=False)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    entry_price = Column(Float, nullable=True)
    sphere = Column(String(50), nullable=True)
    market_price = Column(Float, nullable=True)

    project = relationship('Project', back_populates='basic_metrics')


class InvestingMetrics(Base):
    __tablename__ = 'investing_metrics'

    id = Column(Integer, primary_key=True, nullable=False)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    fundraise = Column(Float, nullable=True)
    fund_level = Column(Text, nullable=True)

    project = relationship('Project', back_populates='investing_metrics')


class SocialMetrics(Base):
    __tablename__ = 'social_metrics'

    id = Column(Integer, primary_key=True, nullable=False)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    twitter = Column(Integer, nullable=True)
    twitterscore = Column(Integer, nullable=True)

    project = relationship('Project', back_populates='social_metrics')


class Tokenomics(Base):
    __tablename__ = 'tokenomics'

    id = Column(Integer, primary_key=True, nullable=False)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    circ_supply = Column(Float, nullable=True)
    total_supply = Column(Float, nullable=True)
    capitalization = Column(Float, nullable=True)
    fdv = Column(Float, nullable=True)

    project = relationship('Project', back_populates='tokenomics')


class FundsProfit(Base):
    __tablename__ = 'funds_profit'

    id = Column(Integer, primary_key=True, nullable=False)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    distribution = Column(Text, nullable=True)
    average_price = Column(Float, nullable=True)
    x_value = Column(Float, nullable=True)

    project = relationship('Project', back_populates='funds_profit')


class TopAndBottom(Base):
    __tablename__ = 'top_and_bottom'

    id = Column(Integer, primary_key=True, nullable=False)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    lower_threshold = Column(Float, nullable=True)
    upper_threshold = Column(Float, nullable=True)

    project = relationship('Project', back_populates='top_and_bottom')


class MarketMetrics(Base):
    __tablename__ = 'market_metrics'

    id = Column(Integer, primary_key=True, nullable=False)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    fail_high = Column(Float, nullable=True)
    growth_low = Column(Float, nullable=True)

    project = relationship('Project', back_populates='market_metrics')


class ManipulativeMetrics(Base):
    __tablename__ = 'manipulative_metrics'

    id = Column(Integer, primary_key=True, nullable=False)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    fdv_fundraise = Column(Float, nullable=True)
    top_100_wallet = Column(Float, nullable=True)

    project = relationship('Project', back_populates='manipulative_metrics')


class NetworkMetrics(Base):
    __tablename__ = 'network_metrics'

    id = Column(Integer, primary_key=True, nullable=False)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    tvl = Column(Float, nullable=True)
    tvl_fdv = Column(Float, nullable=True)

    project = relationship('Project', back_populates='network_metrics')


class AgentAnswer(Base):
    __tablename__ = 'agentanswer'

    id = Column(Integer, primary_key=True, nullable=False)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    answer = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    project = relationship('Project', back_populates='agentanswer')
