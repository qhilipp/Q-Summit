import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Button from '../Button/Button.jsx';
import { useUserData } from '../../context/UserDataContext';
import './TravelMonthsInfo.css';

// Import the default API URL from ResultsPage
const DEFAULT_API_URL = 'http://localhost:8000/search_universities';

const TravelMonthsInfo = () => {
  const navigate = useNavigate();
  const { userData, updateUserData, sendDataToApi } = useUserData();
  const [startMonth, setStartMonth] = useState('');
  const [startYear, setStartYear] = useState('');
  const [endMonth, setEndMonth] = useState('');
  const [endYear, setEndYear] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Generate month options
  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  // Generate year options (current year + 5 years ahead)
  const currentYear = new Date().getFullYear();
  const years = Array.from({length: 6}, (_, i) => (currentYear + i).toString());

  // Validate date selections
  const isValidDateSelection = () => {
    if (!startMonth || !startYear || !endMonth || !endYear) {
      return false;
    }

    const start = new Date(`${startMonth} 1, ${startYear}`);
    const end = new Date(`${endMonth} 1, ${endYear}`);
    
    return start <= end;
  };

  // Handle continue click
  const handleContinue = async () => {
    if (!isValidDateSelection()) {
      setError('Please select valid start and end dates.');
      return;
    }

    try {
      setLoading(true);
      
      // Update the context with the travel dates
      await updateUserData({
        'start-month': startMonth,
        'start-year': startYear,
        'end-month': endMonth,
        'end-year': endYear
      });
      
      // Navigate directly to results page (API call will happen there)
      navigate('/results');
    } catch (err) {
      setError('There was a problem processing your request. Please try again.');
      console.error('Error:', err);
      setLoading(false);
    }
  };

  // Skip option
  const handleSkip = () => {
    // Just navigate to results page
    navigate('/results');
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
      className="travel-months-container"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.h1 className="travel-heading" variants={titleVariants}>
        When would you like to travel? (roughly)
      </motion.h1>

      {error && <div className="error-message">{error}</div>}

      <div className="dates-container">
        <div className="date-section">
          <h3>Start Date</h3>
          <div className="date-inputs">
            <select 
              value={startMonth} 
              onChange={(e) => setStartMonth(e.target.value)}
              className="month-select"
            >
              <option value="">Month</option>
              {months.map(month => (
                <option key={`start-${month}`} value={month}>{month}</option>
              ))}
            </select>
            
            <select 
              value={startYear} 
              onChange={(e) => setStartYear(e.target.value)}
              className="year-select"
            >
              <option value="">Year</option>
              {years.map(year => (
                <option key={`start-${year}`} value={year}>{year}</option>
              ))}
            </select>
          </div>
        </div>
        
        <div className="date-section">
          <h3>End Date</h3>
          <div className="date-inputs">
            <select 
              value={endMonth} 
              onChange={(e) => setEndMonth(e.target.value)}
              className="month-select"
            >
              <option value="">Month</option>
              {months.map(month => (
                <option key={`end-${month}`} value={month}>{month}</option>
              ))}
            </select>
            
            <select 
              value={endYear} 
              onChange={(e) => setEndYear(e.target.value)}
              className="year-select"
            >
              <option value="">Year</option>
              {years.map(year => (
                <option key={`end-${year}`} value={year}>{year}</option>
              ))}
            </select>
          </div>
        </div>
      </div>
      
      <div className="buttons-container">
        <Button 
          onClick={handleContinue} 
          disabled={loading || !isValidDateSelection()}
          className={loading ? 'loading' : ''}
        >
          {loading ? 'Processing...' : 'Find My Universities'}
        </Button>
        
        <Button 
          onClick={handleSkip} 
          disabled={loading}
          className="skip-button"
        >
          <span className="top-text">Skip</span>
          <span className="bottom-text">I'm flexible</span>
        </Button>
      </div>
    </motion.div>
  );
};

export default TravelMonthsInfo; 