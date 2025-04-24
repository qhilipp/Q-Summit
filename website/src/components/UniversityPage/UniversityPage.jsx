import React, { useEffect, useState, useRef } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useUserData } from '../../context/UserDataContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import './UniversityPage.css';

const UniversityPage = () => {
  const { id } = useParams();
  const location = useLocation();
  const universityData = location.state?.university;
  const { userData } = useUserData();
  const [plan, setPlan] = useState(null);
  const [quotes, setQuotes] = useState(null);
  const [isLoadingPlan, setIsLoadingPlan] = useState(false);
  const [isLoadingQuotes, setIsLoadingQuotes] = useState(false);
  const [error, setError] = useState(null);
  const lastRequestTime = useRef(0);

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
    return `details-rating-chip ${ranking}`;
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

  useEffect(() => {
    console.log("University Data:", universityData);
    const fetchApplicationPlan = async () => {
      const now = Date.now();
      if (now - lastRequestTime.current < 1000) {
        console.log("Throttling request - less than 1 second since last request");
        return;
      }
      lastRequestTime.current = now;

      console.log("Fetching application plan");
      setIsLoadingPlan(true);
      setError(null);
      
      try {
        const myHeaders = new Headers();
        myHeaders.append("Content-Type", "application/json");

        const raw = JSON.stringify({
          "home_university": userData.university || "Muenster",
          "target_university": universityData?.title || decodeURIComponent(id),
          "major": userData.major || "Computer Science"
        });

        const requestOptions = {
          method: "POST",
          headers: myHeaders,
          body: raw,
          redirect: "follow"
        };
        console.log(requestOptions);
        const response = await fetch("http://localhost:8000/application_plan", requestOptions);
        console.log("Got it!");
        const result = await response.json();
        console.log(result);
        setPlan(result.plan);
      } catch (error) {
        console.error('Error fetching application plan:', error);
        setError('Failed to fetch your application plan. Please try again later.');
      } finally {
        setIsLoadingPlan(false);
      }
    };

    fetchApplicationPlan();
  }, [userData.university, userData.major, id, universityData]);

  useEffect(() => {
    const fetchQuotes = async () => {
      setIsLoadingQuotes(true);
      try {
        const response = await fetch(`http://localhost:8000/university_details/${encodeURIComponent(universityData?.title || decodeURIComponent(id))}`, {
          method: "GET",
          redirect: "follow"
        });
        const result = await response.json();
        setQuotes(result.quotes);
      } catch (error) {
        console.error('Error fetching quotes:', error);
      } finally {
        setIsLoadingQuotes(false);
      }
    };

    fetchQuotes();
  }, [id, universityData]);

  return (
    <motion.div 
      className="university-page-container"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <div className="scrollable-content">
        <div className="content-wrapper">
          <div className="left-column">
            <div className="details-card">
              <h3 className="details-title">{universityData?.title}</h3>
              
              <div className="details-image-container">
                <img 
                  src={universityData?.image} 
                  alt={universityData?.title}
                  className="details-image"
                />
              </div>
              
              <div className="details-content">
                <p className="details-description">{universityData?.description}</p>
                
                <div className="details-stats">
                  <div className="details-stat-item">
                    <span className="details-stat-icon">🏆</span>
                    <span className="details-stat-label">Ranking</span>
                    <span className={`details-stat-value ${getRankingClass(universityData?.ranking)}`}>
                      {getRankingLabel(universityData?.ranking)}
                    </span>
                  </div>
                  <div className="details-stat-item">
                    <span className="details-stat-icon">👨‍🎓</span>
                    <span className="details-stat-label">Students</span>
                    <span className="details-stat-value">
                      {universityData?.student_count?.toLocaleString()}
                    </span>
                  </div>
                  <div className="details-stat-item">
                    <span className="details-stat-icon">📊</span>
                    <span className="details-stat-label">Min. GPA</span>
                    <span className="details-stat-value">
                      {universityData?.gpa?.toFixed(1)}
                    </span>
                  </div>
                </div>
                
                <div className="details-terms">
                  <h4 className="details-section-label">Terms</h4>
                  <div className="details-terms-list">
                    {universityData?.terms?.map((term, index) => (
                      <span key={index} className="details-term-badge">
                        {getTermEmoji(term)} {term}
                      </span>
                    ))}
                  </div>
                </div>
                
                <div className="details-languages">
                  <h4 className="details-section-label">Languages</h4>
                  <div className="details-languages-list">
                    {universityData?.languages?.map((language, index) => (
                      <span key={index} className="details-language-badge">
                        {getLanguageFlag(language)} {language}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="quotes-section">
              {isLoadingQuotes ? (
                <div className="quotes-loading">
                  <div className="quotes-spinner"></div>
                  <p>Loading quotes...</p>
                </div>
              ) : quotes && quotes.length > 0 ? (
                <div className="quotes-list">
                  {quotes.map((quote, index) => (
                    <motion.div 
                      key={index}
                      className="quote-card"
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                    >
                      <p className="quote-text">{quote.quote}</p>
                      <a 
                        href={quote.source_link} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        className="quote-source"
                      >
                        Source →
                      </a>
                    </motion.div>
                  ))}
                </div>
              ) : null}
            </div>
          </div>

          <div className="plan-section">
            {isLoadingPlan ? (
              <div className="plan-loading">
                <div className="plan-spinner"></div>
                <p>Crafting your plan...</p>
              </div>
            ) : error ? (
              <div className="plan-error">
                {error}
              </div>
            ) : plan ? (
              <div className="plan-content">
                <motion.h1 
                  className="page-title"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.1 }}
                >
                  <div className="title-gradient-wrapper">
                    {Array.from("Your plan").map((char, index) => (
                      <motion.span
                        key={index}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{
                          duration: 0.4,
                          delay: index * 0.1,
                          ease: [0.2, 0.65, 0.3, 0.9]
                        }}
                      >
                        {char === " " ? "\u00A0" : char}
                      </motion.span>
                    ))}
                  </div>
                </motion.h1>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw]}
                  components={{
                    h1: ({node, ...props}) => <h1 style={{color: '#ffffff'}} {...props} />,
                    h2: ({node, ...props}) => <h2 style={{color: '#ffffff'}} {...props} />,
                    h3: ({node, ...props}) => <h3 style={{color: '#ffffff'}} {...props} />,
                    p: ({node, ...props}) => <p style={{color: '#ffffff', lineHeight: '1.6'}} {...props} />,
                    ul: ({node, ...props}) => <ul style={{color: '#ffffff', marginLeft: '1.5rem'}} {...props} />,
                    ol: ({node, ...props}) => <ol style={{color: '#ffffff', marginLeft: '1.5rem'}} {...props} />,
                    li: ({node, ...props}) => <li style={{color: '#ffffff', marginBottom: '0.5rem'}} {...props} />,
                    a: ({node, ...props}) => <a style={{color: '#64b5f6'}} {...props} />,
                    code: ({node, inline, ...props}) => (
                      inline ? 
                        <code style={{background: 'rgba(255, 255, 255, 0.1)', padding: '0.2em 0.4em', borderRadius: '3px'}} {...props} /> :
                        <code style={{display: 'block', background: 'rgba(0, 0, 0, 0.2)', padding: '1em', borderRadius: '4px', overflowX: 'auto'}} {...props} />
                    )
                  }}
                >
                  {plan}
                </ReactMarkdown>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default UniversityPage; 