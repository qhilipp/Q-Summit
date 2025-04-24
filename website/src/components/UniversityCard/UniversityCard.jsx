import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import './UniversityCard.css';

const UniversityCard = ({ university, onClick }) => {
  const navigate = useNavigate();

  const getLanguageFlag = (language) => {
    const flags = {
      'English': '🇬🇧',
      'German': '🇩🇪',
      'French': '🇫🇷',
      'Spanish': '🇪🇸',
      'Italian': '🇮🇹',
      'Chinese': '🇨🇳',
      'Japanese': '🇯🇵',
      'Korean': '🇰🇷',
      'Russian': '🇷🇺',
      'Arabic': '🇦🇪',
      'Portuguese': '🇵🇹',
      'Dutch': '🇳🇱',
      'Swedish': '🇸🇪',
      'Norwegian': '🇳🇴',
      'Finnish': '🇫🇮',
      'Danish': '🇩🇰',
      'Turkish': '🇹🇷',
      'Polish': '🇵🇱',
      'Czech': '🇨🇿',
      'Greek': '🇬🇷',
      'Hungarian': '🇭🇺',
    };
    return flags[language] || '🌐';
  };

  const getRankingLabel = (ranking) => {
    if (ranking === 'high') return 'High';
    if (ranking === 'mid') return 'Mid';
    if (ranking === 'low') return 'Low';
    return ranking;
  };

  const getRankingClass = (ranking) => {
    return `rating-chip ${ranking}`;
  };

  const truncateDescription = (text, maxLength = 120) => {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  const getTermEmoji = (term) => {
    const emojis = {
      'Fall': '🍂',
      'Spring': '🌸',
      'Summer': '☀️',
      'Winter': '❄️'
    };
    return emojis[term] || '📅';
  };

  const formatCost = (cost) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(cost);
  };

  const handleSelect = (e) => {
    e.stopPropagation(); // Prevent card click event from firing
    navigate(`/university/${university.id}`);
  };

  return (
    <motion.div 
      className="university-card"
      onClick={() => onClick(university)}
      whileHover={{ 
        boxShadow: '0 10px 25px rgba(0, 0, 0, 0.3)',
        border: '1px solid rgba(255, 255, 255, 0.5)'
      }}
      transition={{ duration: 0.2 }}
    >
      <h3 className="university-title">{university.title}</h3>
      
      <div className="image-container">
        <img 
          src={university.image} 
          alt={university.title}
          className="university-image"
        />
      </div>
      
      <div className="university-details">
        <p className="university-description">{truncateDescription(university.description)}</p>
        
        <div className="university-stats">
          <div className="stat-item">
            <span className="stat-icon">🏆</span>
            <span className="stat-label">Ranking</span>
            <span className={`stat-value ${getRankingClass(university.ranking)}`}>
              {getRankingLabel(university.ranking)}
            </span>
          </div>
          <div className="stat-item">
            <span className="stat-icon">👨‍🎓</span>
            <span className="stat-label">Students</span>
            <span className="stat-value">{university.student_count.toLocaleString()}</span>
          </div>
          <div className="stat-item">
            <span className="stat-icon">📊</span>
            <span className="stat-label">Min. GPA</span>
            <span className="stat-value">{university.gpa.toFixed(1)}</span>
          </div>
        </div>
        
        <div className="university-terms">
          <h4 className="section-label">Terms</h4>
          <div className="terms-list">
            {university.terms.map((term, index) => (
              <span key={index} className="term-badge">
                {getTermEmoji(term)} {term}
              </span>
            ))}
          </div>
        </div>
        
        <div className="university-language">
          <h4 className="section-label">Language</h4>
          <div className="languages-list">
            {university.languages.map((language, index) => (
              <span key={index} className="language-badge">
                {getLanguageFlag(language)} {language}
              </span>
            ))}
          </div>
        </div>
      </div>

      <button className="select-button" onClick={handleSelect}>
        Select University →
      </button>
    </motion.div>
  );
};

export default UniversityCard; 