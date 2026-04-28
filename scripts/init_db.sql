-- VocabWeaver 数据库初始化脚本
-- 创建所需的表结构

-- ============================================================
-- Users 表
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(255) PRIMARY KEY,            -- 用户ID，兼容 'anonymous'
    username VARCHAR(255),                  -- 用户名（可选）
    email VARCHAR(255) UNIQUE,              -- 邮箱（可选）
    password_hash VARCHAR(255),             -- 密码哈希（可选）
    avatar_url VARCHAR(500),                -- 头像URL（可选）
    preferences JSONB DEFAULT '{}',         -- 用户偏好（默认风格、语言等）
    is_anonymous BOOLEAN DEFAULT FALSE,     -- 是否为匿名用户
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 预置匿名用户（兼容现有功能）
INSERT INTO users (id, is_anonymous)
VALUES ('anonymous', TRUE)
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- Sessions 表
-- ============================================================
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    total_episodes INTEGER DEFAULT 1,
    current_episode INTEGER DEFAULT 1,
    style VARCHAR(100) DEFAULT 'adventure',
    status VARCHAR(50) DEFAULT 'active',
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, session_id)
);

-- ============================================================
-- Story Bibles 表
-- ============================================================
CREATE TABLE IF NOT EXISTS story_bibles (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    content JSONB,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(session_id)
);

-- ============================================================
-- Episode States 表
-- ============================================================
CREATE TABLE IF NOT EXISTS episode_states (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    episode_num INTEGER NOT NULL,
    transcript TEXT,
    target_words JSONB,
    used_words JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(session_id, episode_num)
);

-- ============================================================
-- 索引
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_session ON sessions(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_episode_states_session ON episode_states(session_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============================================================
-- 外键约束（保证数据完整性）
-- ============================================================
ALTER TABLE sessions
DROP CONSTRAINT IF EXISTS fk_sessions_user;

ALTER TABLE sessions
ADD CONSTRAINT fk_sessions_user
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- ============================================================
-- 更新时间触发器
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_story_bibles_updated_at
    BEFORE UPDATE ON story_bibles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_episode_states_updated_at
    BEFORE UPDATE ON episode_states
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
