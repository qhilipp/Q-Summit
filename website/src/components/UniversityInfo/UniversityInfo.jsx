import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useState, useEffect, useCallback, useRef } from 'react';
import Button from '../Button/Button.jsx';
import { useUserData } from '../../context/UserDataContext';
import './UniversityInfo.css';

const getFlagEmoji = (countryCode) => {
  if (!countryCode) return '';
  const codePoints = countryCode
    .toUpperCase()
    .split('')
    .map(char => 127397 + char.charCodeAt());
  return String.fromCodePoint(...codePoints);
};

const UniversityInfo = () => {
  const navigate = useNavigate();
  const { updateUserData } = useUserData();
  const [university, setUniversity] = useState('');
  const [studyField, setStudyField] = useState('');
  const [universitySuggestions, setUniversitySuggestions] = useState([]);
  const [showUniversitySuggestions, setShowUniversitySuggestions] = useState(false);
  const [isLoadingUniversity, setIsLoadingUniversity] = useState(false);
  const suggestionsRef = useRef(null);

  const fetchUniversities = useCallback(async (query) => {
    if (query.length < 3) {
      console.log('Query too short:', query);
      setUniversitySuggestions([]);
      setShowUniversitySuggestions(false);
      return;
    }

    console.log('Fetching universities for query:', query);
    setIsLoadingUniversity(true);
    try {
      const response = await fetch(
        `https://api.openalex.org/institutions?search=${encodeURIComponent(query)}&per_page=10`
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Raw API response:', data);
      
      if (data.results && Array.isArray(data.results)) {
        const universities = data.results
          .filter(institution => institution.display_name && institution.country_code)
          .map(institution => ({
            name: institution.display_name,
            country: institution.country_code,
            flag: getFlagEmoji(institution.country_code),
            id: institution.id
          }));
        
        console.log('Processed universities:', universities);
        console.log('Number of suggestions:', universities.length);
        setUniversitySuggestions(universities);
        setShowUniversitySuggestions(universities.length > 0);
      } else {
        console.log('No valid results in API response');
        setUniversitySuggestions([]);
        setShowUniversitySuggestions(false);
      }
    } catch (error) {
      console.error('Error fetching universities:', error);
      setUniversitySuggestions([]);
      setShowUniversitySuggestions(false);
    } finally {
      setIsLoadingUniversity(false);
    }
  }, []);

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      if (university.trim().length >= 3) {
        fetchUniversities(university);
      } else {
        setUniversitySuggestions([]);
        setShowUniversitySuggestions(false);
      }
    }, 300);

    return () => clearTimeout(debounceTimer);
  }, [university, fetchUniversities]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target)) {
        setShowUniversitySuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleUniversitySuggestionClick = (suggestion) => {
    setUniversity(suggestion.name);
    setShowUniversitySuggestions(false);
  };

  const handleContinue = async () => {
    // Save university and major to context
    await updateUserData({
      university: university.trim(),
      major: studyField.trim()
    });
    
    console.log('University and major data saved:', university.trim(), studyField.trim());
    
    // Navigate to next page
    navigate('/gpa');
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: 1,
        when: "beforeChildren",
        staggerChildren: 0.1
      }
    }
  };

  const titleVariants = {
    hidden: { y: 50, opacity: 0 },
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

  const buttonVariants = {
    hidden: { scale: 0, opacity: 0 },
    visible: {
      scale: 1,
      opacity: 1,
      transition: {
        type: "spring",
        stiffness: 200,
        damping: 15,
        delay: 0.5
      }
    },
    hover: {
      scale: 1.05,
      transition: {
        type: "spring",
        stiffness: 400,
        damping: 10
      }
    }
  };

  return (
    <motion.div
      className="university-container"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.h1 className="welcome-heading" variants={titleVariants}>
        Let's start with some basic info
      </motion.h1>

      <div className="input-container">
        <div className="input-wrapper" ref={suggestionsRef}>
          <input 
            type="text" 
            placeholder="Your University" 
            className="info-input"
            value={university}
            onChange={(e) => setUniversity(e.target.value)}
            onFocus={() => university.length >= 3 && setShowUniversitySuggestions(true)}
          />
          {isLoadingUniversity && <div className="loading-indicator">Searching...</div>}
          {showUniversitySuggestions && universitySuggestions.length > 0 && (
            <div className="suggestions-list">
              {universitySuggestions.map((suggestion) => (
                <div
                  key={suggestion.id}
                  className="suggestion-item"
                  onClick={() => handleUniversitySuggestionClick(suggestion)}
                >
                  <span className="university-name">{suggestion.name}</span>
                  <span className="university-flag">{suggestion.flag}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        
        <input 
          type="text" 
          placeholder="Your Field of Study" 
          className="info-input"
          value={studyField}
          onChange={(e) => setStudyField(e.target.value)}
        />
      </div>
      
      <Button onClick={handleContinue}>
        Let's go
      </Button>
    </motion.div>
  );
};

export default UniversityInfo; 