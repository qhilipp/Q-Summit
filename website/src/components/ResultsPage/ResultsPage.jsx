import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useUserData } from '../../context/UserDataContext';
import './ResultsPage.css';

// This should be replaced with the actual API URL
const DEFAULT_API_URL = 'https://api.example.com/submit-preferences';

const ResultsPage = ({ apiUrl }) => {
  const navigate = useNavigate();
  const { userData, sendDataToApi } = useUserData();
  const [isLoading, setIsLoading] = useState(true);
  const [universities, setUniversities] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchUniversities = async () => {
      try {
        setIsLoading(true);
        const response = await sendDataToApi(apiUrl || DEFAULT_API_URL);
        
        // Assuming the API returns an array of university names
        if (Array.isArray(response)) {
          setUniversities(response);
        } else if (response && Array.isArray(response.universities)) {
          // Alternative response format
          setUniversities(response.universities);
        } else {
          throw new Error('Invalid response format');
        }
      } catch (error) {
        console.error('Error fetching universities:', error);
        setError('Failed to find matching universities. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchUniversities();
  }, [sendDataToApi, apiUrl]);

  const handleUniversityClick = (university) => {
    // Handle university selection (can be expanded later)
    console.log('Selected university:', university);
    // Navigate to university info or detail page
    navigate('/university');
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: 0.8,
        when: "beforeChildren",
        staggerChildren: 0.1
      }
    }
  };

  const titleVariants = {
    hidden: { y: -20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        type: "spring",
        stiffness: 100,
        damping: 10
      }
    }
  };

  const listItemVariants = {
    hidden: { x: 20, opacity: 0 },
    visible: {
      x: 0,
      opacity: 1,
      transition: {
        type: "spring",
        stiffness: 100,
        damping: 10
      }
    }
  };

  return (
    <motion.div
      className="results-container"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.h1 className="results-heading" variants={titleVariants}>
        {isLoading ? "We're looking for your perfect universities" : "Your University Matches 🏫❤️🧑‍🎓"}
      </motion.h1>

      {isLoading ? (
        <div className="spinner-container">
          <div className="spinner"></div>
          <p className="loading-text">Analyzing your preferences...</p>
        </div>
      ) : error ? (
        <div className="error-container">
          <p className="error-message">{error}</p>
          <button className="retry-button" onClick={() => navigate('/travel-months')}>
            Try Again
          </button>
        </div>
      ) : (
        <div className="results-content">
          <p className="results-description">
            Here are some universities that match your preferences:
          </p>
          <div className="universities-scroll-container">
            <div className="universities-list">
              {universities.map((university, index) => (
                <motion.div
                  key={index}
                  className="university-card"
                  variants={listItemVariants}
                  onClick={() => handleUniversityClick(university)}
                >
                  <h3 className="university-name">{university}</h3>
                </motion.div>
              ))}
              {universities.length === 0 && (
                <p className="no-results">No matches found. Try adjusting your preferences.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
};

export default ResultsPage; 