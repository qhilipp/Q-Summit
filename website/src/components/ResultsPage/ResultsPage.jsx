import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useState, useEffect, useRef } from 'react';
import { useUserData } from '../../context/UserDataContext';
import UniversityCard from '../UniversityCard/UniversityCard';
import UniversityDetailsPopup from '../UniversityDetailsPopup/UniversityDetailsPopup';
import './ResultsPage.css';

// This is the endpoint for university search
const DEFAULT_API_URL = 'http://localhost:8000/search_universities';

// Toggle this to use dummy data instead of API calls
const USE_DUMMY_DATA = false;

// Sample university data for development and testing
const mockUniversities = [
  {
    title: "University of the Fraser Valley",
    description: "The University of the Fraser Valley (UFV) is a public university located in Abbotsford, British Columbia, Canada. Known for its strong emphasis on student success and community engagement, UFV offers a wide range of undergraduate and graduate programs.",
    image: "https://cuebc.org/wp-content/uploads/2020/09/4292864791_84b79af7ca_b.jpg",
    student_count: 15000,
    ranking: "mid",
    gpa: 3.0,
    terms: ["Fall", "Spring", "Summer"],
    languages: ["English"],
  },
  {
    title: "University of British Columbia",
    description: "The University of British Columbia is a public research university with campuses in Vancouver and Kelowna, British Columbia. Established in 1908, it is British Columbia's oldest university.",
    image: "https://www.columbia.edu/content/sites/default/files/styles/cu_crop/public/content/Morningside%20Campus%20at%20Dusk%202.jpg?itok=SkwvzD5S",
    student_count: 65000,
    ranking: "high",
    gpa: 3.5,
    terms: ["Fall", "Spring"],
    languages: ["English", "French"],
  },
  {
    title: "University of Alberta",
    description: "The University of British Columbia is a public research university with campuses in Vancouver and Kelowna, British Columbia. Established in 1908, it is British Columbia's oldest university.",
    image: "https://www.ualberta.ca/en/university-relations/media-library/community-relations/photos/12784-06-115-athabasca02.png",
    student_count: 65000,
    ranking: "low",
    gpa: 2.5,
    terms: ["Summer", "Spring"],
    languages: ["Spanish", "French"],
  }
];

const ResultsPage = () => {
  const navigate = useNavigate();
  const { userData } = useUserData();
  const [isLoading, setIsLoading] = useState(true);
  const [universities, setUniversities] = useState([]);
  const [error, setError] = useState('');
  const scrollContainerRef = useRef(null);
  const [selectedUniversity, setSelectedUniversity] = useState(null);
  const [isPopupOpen, setIsPopupOpen] = useState(false);

  useEffect(() => {
    // Call API when component mounts
    fetchUniversities();
  }, [userData]);

  const fetchUniversities = async () => {
    setIsLoading(true);
    setError(null);

    if (USE_DUMMY_DATA) {
      // Simulate loading delay when using dummy data
      setTimeout(() => {
        setUniversities(mockUniversities);
        setIsLoading(false);
      }, 1500);
      return;
    }

    try {
      const myHeaders = new Headers();
      myHeaders.append("Content-Type", "application/json");

      // Prepare request body with user preferences
      const raw = JSON.stringify({
        "university": userData.university || "",
        "major": userData.major || "",
        "gpa": userData.gpa || 3.5,
        "languages": userData.languages || ["English"],
        "budget": userData.budget || 1000,
        "start_month": userData.startMonth || 9,
        "start_year": userData.startYear || 2024,
        "end_month": userData.endMonth || 6,
        "end_year": userData.endYear || 2025
      });

      const requestOptions = {
        method: "POST",
        headers: myHeaders,
        body: raw,
        redirect: "follow"
      };

      const response = await fetch(DEFAULT_API_URL, requestOptions);

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      setUniversities(data);
    } catch (err) {
      console.error("Error fetching universities:", err);
      setError(err.message || "Failed to fetch university matches");
    } finally {
      setIsLoading(false);
    }
  };

  const handleUniversityClick = (university) => {
    // Handle university selection and show popup
    console.log('Selected university:', university);
    setSelectedUniversity(university);
    setIsPopupOpen(true);
  };

  const closePopup = () => {
    setIsPopupOpen(false);
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
    <>
      <motion.div
        className="results-container"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <motion.h1 className="results-heading" variants={titleVariants}>
          {isLoading ? "We're looking for your perfect universities" : "Your University Matches 🏫❤️🧑‍🎓"}
          {USE_DUMMY_DATA && <span className="dummy-data-badge">Demo Mode</span>}
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

      {/* University Details Popup */}
      {selectedUniversity && (
        <UniversityDetailsPopup 
          university={selectedUniversity}
          isOpen={isPopupOpen}
          onClose={closePopup}
        />
      )}
    </>
  );
};

export default ResultsPage; 