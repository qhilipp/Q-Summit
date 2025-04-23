import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useState, useEffect, useRef } from 'react';
import Button from '../Button/Button.jsx';
import { useUserData } from '../../context/UserDataContext';
import './LanguagesInfo.css';

// Hardcoded list of languages with flags
const LANGUAGES = [
  { name: 'English', code: 'GB', flag: '🇬🇧' },
  { name: 'German', code: 'DE', flag: '🇩🇪' },
  { name: 'French', code: 'FR', flag: '🇫🇷' },
  { name: 'Spanish', code: 'ES', flag: '🇪🇸' },
  { name: 'Italian', code: 'IT', flag: '🇮🇹' },
  { name: 'Portuguese', code: 'PT', flag: '🇵🇹' },
  { name: 'Dutch', code: 'NL', flag: '🇳🇱' },
  { name: 'Chinese', code: 'CN', flag: '🇨🇳' },
  { name: 'Japanese', code: 'JP', flag: '🇯🇵' },
  { name: 'Korean', code: 'KR', flag: '🇰🇷' },
  { name: 'Russian', code: 'RU', flag: '🇷🇺' },
  { name: 'Arabic', code: 'SA', flag: '🇸🇦' },
  { name: 'Hindi', code: 'IN', flag: '🇮🇳' },
  { name: 'Swedish', code: 'SE', flag: '🇸🇪' },
  { name: 'Norwegian', code: 'NO', flag: '🇳🇴' },
  { name: 'Danish', code: 'DK', flag: '🇩🇰' },
  { name: 'Finnish', code: 'FI', flag: '🇫🇮' },
  { name: 'Polish', code: 'PL', flag: '🇵🇱' },
  { name: 'Czech', code: 'CZ', flag: '🇨🇿' },
  { name: 'Greek', code: 'GR', flag: '🇬🇷' },
  { name: 'Turkish', code: 'TR', flag: '🇹🇷' }
];

const LanguagesInfo = () => {
  const navigate = useNavigate();
  const { updateUserData } = useUserData();
  const [inputValue, setInputValue] = useState('');
  const [selectedLanguages, setSelectedLanguages] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [error, setError] = useState('');
  const suggestionsRef = useRef(null);

  // Filter languages based on input
  useEffect(() => {
    if (inputValue.trim() === '') {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const filtered = LANGUAGES.filter(
      lang => lang.name.toLowerCase().includes(inputValue.toLowerCase()) &&
      !selectedLanguages.some(selected => selected.name === lang.name)
    );
    
    setSuggestions(filtered);
    setShowSuggestions(filtered.length > 0);
  }, [inputValue, selectedLanguages]);

  // Close suggestions on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
    if (error) setError('');
  };

  const handleSelectLanguage = (language) => {
    if (selectedLanguages.length >= 5) {
      setError('You can only select up to 5 languages');
      return;
    }
    
    setSelectedLanguages([...selectedLanguages, language]);
    setInputValue('');
    setShowSuggestions(false);
  };

  const handleRemoveLanguage = (languageToRemove) => {
    setSelectedLanguages(selectedLanguages.filter(
      lang => lang.name !== languageToRemove.name
    ));
    
    if (error) setError('');
  };

  const handleContinue = () => {
    if (selectedLanguages.length === 0) {
      setError('Please select at least one language');
      return;
    }
    
    // Save languages to context
    updateUserData({ 
      languages: selectedLanguages.map(lang => lang.name) 
    });
    
    // Proceed to next page
    navigate('/budget');
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

  return (
    <motion.div
      className="languages-container"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.h1 className="languages-heading" variants={titleVariants}>
        What languages do you speak?
      </motion.h1>

      <div className="input-container">
        <div className="selected-languages">
          {selectedLanguages.map((lang, index) => (
            <div key={index} className="language-chip">
              <span className="language-flag">{lang.flag}</span>
              <span className="language-name">{lang.name}</span>
              <button className="remove-language" onClick={() => handleRemoveLanguage(lang)}>X</button>
            </div>
          ))}
        </div>

        <div className="input-wrapper" ref={suggestionsRef}>
          <input 
            type="text" 
            placeholder={selectedLanguages.length >= 5 ? "Maximum languages reached" : "Type a language..."}
            className={`info-input ${error ? 'error' : ''}`}
            value={inputValue}
            onChange={handleInputChange}
            disabled={selectedLanguages.length >= 5}
          />
          
          {showSuggestions && suggestions.length > 0 && (
            <div className="suggestions-list">
              {suggestions.map((lang, index) => (
                <div 
                  key={index} 
                  className="suggestion-item"
                  onClick={() => handleSelectLanguage(lang)}
                >
                  <span className="language-name">{lang.name}</span>
                  <span className="language-flag">{lang.flag}</span>
                </div>
              ))}
            </div>
          )}
          
          {error && <div className="error-message">{error}</div>}
        </div>
      </div>
      
      <Button onClick={handleContinue}>
        Continue
      </Button>
    </motion.div>
  );
};

export default LanguagesInfo; 