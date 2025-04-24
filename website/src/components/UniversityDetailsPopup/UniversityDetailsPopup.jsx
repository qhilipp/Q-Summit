import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './UniversityDetailsPopup.css';
import { useNavigate } from 'react-router-dom';

const UniversityDetailsPopup = ({ university, isOpen, onClose }) => {
  const navigate = useNavigate();
  const [quotes, setQuotes] = useState([]);
  const [isLoadingQuotes, setIsLoadingQuotes] = useState(false);

  useEffect(() => {
    if (isOpen && university) {
      setIsLoadingQuotes(true);
      const requestOptions = {
        method: "GET",
        redirect: "follow"
      };

      fetch(`http://localhost:8000/university_details/${university.id || 'uni_muenster'}`, requestOptions)
        .then((response) => response.json())
        .then((result) => {
          setQuotes(result.quotes || []);
          setIsLoadingQuotes(false);
        })
        .catch((error) => {
          console.error("Error fetching quotes:", error);
          setIsLoadingQuotes(false);
        });
    }
  }, [isOpen, university]);

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

  const getTermEmoji = (term) => {
    const emojis = {
      'Fall': '🍂',
      'Spring': '🌸',
      'Summer': '☀️',
      'Winter': '❄️'
    };
    return emojis[term] || '📅';
  };

  // Animation variants for the popup
  const backdropVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1 }
  };

  const popupVariants = {
    hidden: { y: 50, opacity: 0 },
    visible: { 
      y: 0, 
      opacity: 1,
      transition: { 
        type: "spring", 
        stiffness: 300, 
        damping: 30 
      } 
    },
    exit: { 
      y: 50, 
      opacity: 0,
      transition: { 
        duration: 0.2 
      } 
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div 
          className="popup-backdrop"
          variants={backdropVariants}
          initial="hidden"
          animate="visible"
          exit="hidden"
          onClick={onClose}
        >
          <motion.div 
            className="university-details-popup"
            variants={popupVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            onClick={e => e.stopPropagation()}
          >
            <button className="close-button" onClick={onClose}>×</button>
            <h3 className="university-title">{university?.title}</h3>
            
            <div className="popup-content">
              <div className="image-container">
                <img 
                  src={university?.image} 
                  alt={university?.title}
                  className="university-image"
                />
              </div>

              <div className="university-details">
                <p className="university-description">{university?.description}</p>
                
                <div className="university-stats">
                  <div className="stat-item">
                    <span className="stat-icon">🏆</span>
                    <span className="stat-label">Ranking</span>
                    <span className={`stat-value ${getRankingClass(university?.ranking)}`}>
                      {getRankingLabel(university?.ranking)}
                    </span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-icon">👨‍🎓</span>
                    <span className="stat-label">Students</span>
                    <span className="stat-value">{university?.student_count?.toLocaleString()}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-icon">📊</span>
                    <span className="stat-label">Min. GPA</span>
                    <span className="stat-value">{university?.gpa?.toFixed(1)}</span>
                  </div>
                </div>
                
                <div className="terms-and-languages">
                  <div className="university-terms">
                    <h4 className="section-label">Terms</h4>
                    <div className="terms-list">
                      {university?.terms?.map((term, index) => (
                        <span key={index} className="term-badge">
                          {getTermEmoji(term)} {term}
                        </span>
                      ))}
                    </div>
                  </div>
                  
                  <div className="university-language">
                    <h4 className="section-label">Languages</h4>
                    <div className="languages-list">
                      {university?.languages?.map((language, index) => (
                        <span key={index} className="language-badge">
                          {getLanguageFlag(language)} {language}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {(isLoadingQuotes || quotes.length > 0) && (
                  <div className="university-quotes">
                    <h4 className="section-label">What Students Say</h4>
                    {isLoadingQuotes ? (
                      <div className="quotes-loading">
                        <div className="quotes-spinner"></div>
                        <span>Loading quotes...</span>
                      </div>
                    ) : (
                      <div className="quotes-list">
                        {quotes.map((quote, index) => (
                          <div key={index} className="quote-item">
                            <p className="quote-text">"{quote.quote}"</p>
                            <a href={quote.source_link} target="_blank" rel="noopener noreferrer" className="quote-source">
                              Source →
                            </a>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <button className="select-button" onClick={() => navigate(`/university/${university.id}`, {
                  state: { university }
                })}>
                  Select University →
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default UniversityDetailsPopup; 