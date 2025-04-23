import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useUserData } from '../../context/UserDataContext';
import UniversityCard from '../UniversityCard/UniversityCard';
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
        
        // Check if response is an array
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

    // For testing - mock data when in development
    if (process.env.NODE_ENV === 'development' && !apiUrl) {
      const mockUniversities = [
        {
          title: "UCSB",
          description: "A public research university with a beautiful coastal campus, offering a wide range of academic programs and research opportunities.",
          images: [
            "https://www.dreamstudiesabroad.com/images/schools/ucsb/rr9772isrc.jpg",
            "https://www.independent.com/wp-content/uploads/2021/09/ucsb-1.jpeg?fit=1200%2C758",
            "https://lmnarchitects.com/wp-content/uploads/2023/09/UCSB_ILP_04.jpg"
          ],
          student_count: 50000,
          ranking: 62,
          gpa: 2.8,
          terms: ["Fall", "Winter", "Spring"],
          costs: 4000,
          language: "English"
        },
        {
          title: "University of Munich",
          description: "One of Germany's oldest and most prestigious universities, known for excellence in research and teaching in the heart of Bavaria.",
          images: [
            "https://cms-cdn.lmu.de/media/lmu-mediapool/die_lmu/pano_muenchen_14_full_2_1_format_m.jpg",
            "https://www.studying-in-germany.org/wp-content/uploads/2018/07/LMU-Munich-University.jpg"
          ],
          student_count: 42000,
          ranking: 32,
          gpa: 3.2,
          terms: ["Winter", "Summer"],
          costs: 1500,
          language: "German"
        },
        {
          title: "University of Tokyo",
          description: "Japan's top university and one of Asia's most prestigious institutions, offering world-class education across various disciplines.",
          images: [
            "https://wanderweib.de/wp-content/uploads/2019/05/todai-1-von-1.jpg",
            "https://resource.study-in-japan.go.jp/image/universityphoto/10076/photo1_1.jpg"
          ],
          student_count: 28000,
          ranking: 24,
          gpa: 3.5,
          terms: ["Spring", "Fall"],
          costs: 5200,
          language: "Japanese"
        },
        {
          title: "University of Tokyo",
          description: "Japan's top university and one of Asia's most prestigious institutions, offering world-class education across various disciplines.",
          images: [
            "https://wanderweib.de/wp-content/uploads/2019/05/todai-1-von-1.jpg",
            "https://resource.study-in-japan.go.jp/image/universityphoto/10076/photo1_1.jpg"
          ],
          student_count: 28000,
          ranking: 24,
          gpa: 3.5,
          terms: ["Spring", "Fall"],
          costs: 5200,
          language: "Japanese"
        },
        {
          title: "University of Tokyo",
          description: "Japan's top university and one of Asia's most prestigious institutions, offering world-class education across various disciplines.",
          images: [
            "https://wanderweib.de/wp-content/uploads/2019/05/todai-1-von-1.jpg",
            "https://resource.study-in-japan.go.jp/image/universityphoto/10076/photo1_1.jpg"
          ],
          student_count: 28000,
          ranking: 24,
          gpa: 3.5,
          terms: ["Spring", "Fall"],
          costs: 5200,
          language: "Japanese"
        },
        {
          title: "University of Tokyo",
          description: "Japan's top university and one of Asia's most prestigious institutions, offering world-class education across various disciplines.",
          images: [
            "https://wanderweib.de/wp-content/uploads/2019/05/todai-1-von-1.jpg",
            "https://resource.study-in-japan.go.jp/image/universityphoto/10076/photo1_1.jpg"
          ],
          student_count: 28000,
          ranking: 24,
          gpa: 3.5,
          terms: ["Spring", "Fall"],
          costs: 5200,
          language: "Japanese"
        },
        {
          title: "University of Tokyo",
          description: "Japan's top university and one of Asia's most prestigious institutions, offering world-class education across various disciplines.",
          images: [
            "https://wanderweib.de/wp-content/uploads/2019/05/todai-1-von-1.jpg",
            "https://resource.study-in-japan.go.jp/image/universityphoto/10076/photo1_1.jpg"
          ],
          student_count: 28000,
          ranking: 24,
          gpa: 3.5,
          terms: ["Spring", "Fall"],
          costs: 5200,
          language: "Japanese"
        },
        {
          title: "University of Tokyo",
          description: "Japan's top university and one of Asia's most prestigious institutions, offering world-class education across various disciplines.",
          images: [
            "https://wanderweib.de/wp-content/uploads/2019/05/todai-1-von-1.jpg",
            "https://resource.study-in-japan.go.jp/image/universityphoto/10076/photo1_1.jpg"
          ],
          student_count: 28000,
          ranking: 24,
          gpa: 3.5,
          terms: ["Spring", "Fall"],
          costs: 5200,
          language: "Japanese"
        }
      ];
      
      setTimeout(() => {
        setUniversities(mockUniversities);
        setIsLoading(false);
      }, 2000); // Simulate loading
    } else {
      fetchUniversities();
    }
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
          <div className="universities-scroll-container">
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