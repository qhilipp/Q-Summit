import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useState, useEffect, useRef } from 'react';
import { useUserData } from '../../context/UserDataContext';
import UniversityCard from '../UniversityCard/UniversityCard';
import './ResultsPage.css';

// This is the endpoint for university search
const DEFAULT_API_URL = 'http://localhost:8000/search_universities';

const ResultsPage = () => {
  const navigate = useNavigate();
  const { userData } = useUserData();
  const [isLoading, setIsLoading] = useState(true);
  const [universities, setUniversities] = useState([]);
  const [error, setError] = useState('');
  const scrollContainerRef = useRef(null);

  useEffect(() => {
    const fetchUniversities = async () => {
      try {
        const headers = new Headers();
        headers.append("Content-Type", "application/json");

        // Use userData from context instead of hardcoded values
        const requestOptions = {
          method: "POST",
          headers: headers,
          body: JSON.stringify(userData),
          redirect: "follow"
        };

        // Show loading state
        setIsLoading(true);
        
        const response = await fetch(DEFAULT_API_URL, requestOptions);
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        setUniversities(result);
        setError('');
      } catch (error) {
        console.error("Error fetching universities:", error);
        setError('Failed to fetch university matches. Please try again.');
        setUniversities([]);
      } finally {
        setIsLoading(false);
      }
    };

    // Call API when component mounts
    fetchUniversities();
  }, [userData]);

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
          <div className="universities-scroll-container" ref={scrollContainerRef}>
            <div className="universities-list">
              {universities.map((university, index) => (
                <UniversityCard 
                  key={index}
                  university={university}
                  onClick={() => handleUniversityClick(university)}
                />
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