import { useState } from 'react';
import { motion } from 'framer-motion';
import './UniversityCard.css';

const UniversityCard = ({ university, onClick }) => {
  // Function to get flag emoji for language
  const getLanguageFlag = (language) => {
    const languageFlags = {
      'English': '🇬🇧',
      'German': '🇩🇪',
      'French': '🇫🇷',
      'Spanish': '🇪🇸',
      'Italian': '🇮🇹',
      'Japanese': '🇯🇵',
      'Chinese': '🇨🇳',
      'Russian': '🇷🇺',
      'Portuguese': '🇵🇹',
      'Korean': '🇰🇷',
      'Arabic': '🇸🇦',
      'Dutch': '🇳🇱',
      'Swedish': '🇸🇪',
      'Greek': '🇬🇷',
      'Turkish': '🇹🇷',
      'Polish': '🇵🇱',
      'Norwegian': '🇳🇴',
      'Finnish': '🇫🇮',
      'Danish': '🇩🇰'
    };
    
    return languageFlags[language] || '🌐';
  };

  // Function to get label for ranking
  const getRankingLabel = (ranking) => {
    if (typeof ranking === 'number') {
      return `#${ranking}`;
    }
    
    const rankingLabels = {
      'high': 'Top Tier',
      'mid': 'Mid Tier',
      'low': 'Developing'
    };
    
    return rankingLabels[ranking] || ranking;
  };

  // Truncate description
  const truncateDescription = (text, maxLength = 120) => {
    if (!text || text.length <= maxLength) return text || '';
    return text.substr(0, maxLength) + '...';
  };

  return (
    <motion.div 
      className="university-card"
      onClick={onClick}
      transition={{ duration: 0.3 }}
    >
      <h3 className="university-title">{university.title}</h3>
      
      <div className="image-carousel">
        {university.image ? (
          <div className="carousel-image-container">
            <img 
              src={university.image} 
              alt={university.title} 
              className="carousel-image"
            />
          </div>
        ) : university.images && university.images.length > 0 ? (
          <div className="carousel-image-container">
            <img 
              src={university.images[0]} 
              alt={university.title} 
              className="carousel-image"
            />
          </div>
        ) : (
          <div className="placeholder-image">
            <span>No Image Available</span>
          </div>
        )}
      </div>
      
      <div className="university-details">
        <div className="university-stats">
          <div className="stat">
            <span className="stat-icon">🏆</span>
            <span className="stat-label">Ranking</span>
            <span className="stat-value">{getRankingLabel(university.ranking)}</span>
          </div>
          <div className="stat">
            <span className="stat-icon">👨‍🎓</span>
            <span className="stat-label">Students</span>
            <span className="stat-value">{university.student_count.toLocaleString()}</span>
          </div>
        </div>
        
        <p className="university-description">{truncateDescription(university.description)}</p>
        
        <div className="university-meta">
          <div className="meta-item">
            <span className="meta-label">Languages</span>
            <div className="terms-list">
              {university.languages ? (
                // New format - array of languages
                university.languages.map((lang, index) => (
                  <span key={index} className="term-badge">
                    {lang} {getLanguageFlag(lang)}
                  </span>
                ))
              ) : university.language ? (
                // Old format - single language
                <span className="language-chip">
                  {university.language} {getLanguageFlag(university.language)}
                </span>
              ) : (
                <span className="language-chip">Not specified</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default UniversityCard; 