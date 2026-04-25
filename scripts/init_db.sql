-- VocabWeaver 数据库初始化脚本
-- 创建所需的表结构

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
    state JSONB,
    transcript TEXT,
    target_words JSONB,
    used_words JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(session_id, episode_num)
);

-- ============================================================
-- Vocabulary Progress 表
-- ============================================================
CREATE TABLE IF NOT EXISTS vocabulary_progress (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    word VARCHAR(255) NOT NULL,
    occurrence_count INTEGER DEFAULT 1,
    contexts JSONB,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(session_id, word)
);

-- ============================================================
-- 索引
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_session ON sessions(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_episode_states_session ON episode_states(session_id);
CREATE INDEX IF NOT EXISTS idx_vocab_progress_session ON vocabulary_progress(session_id);
CREATE INDEX IF NOT EXISTS idx_vocab_progress_word ON vocabulary_progress(word);

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
