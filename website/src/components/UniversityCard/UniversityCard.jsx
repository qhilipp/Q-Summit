import { useState } from 'react';
import { motion } from 'framer-motion';
import './UniversityCard.css';

const UniversityCard = ({ university, onClick }) => {
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  
  // Handle image navigation
  const nextImage = (e) => {
    e.stopPropagation();
    setCurrentImageIndex((prevIndex) => 
      prevIndex === university.images.length - 1 ? 0 : prevIndex + 1
    );
  };
  
  const prevImage = (e) => {
    e.stopPropagation();
    setCurrentImageIndex((prevIndex) => 
      prevIndex === 0 ? university.images.length - 1 : prevIndex - 1
    );
  };

  // Format costs with currency symbol
  const formattedCosts = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(university.costs);

  // Truncate description
  const truncateDescription = (text, maxLength = 120) => {
    if (text.length <= maxLength) return text;
    return text.substr(0, maxLength) + '...';
  };

  return (
    <motion.div 
      className="university-card"
      onClick={onClick}
      whileHover={{ 
        y: -5,
        boxShadow: '0 8px 15px rgba(0, 0, 0, 0.2)',
        borderColor: 'rgba(52, 152, 219, 0.5)'
      }}
      transition={{ duration: 0.3 }}
    >
      <h3 className="university-title">{university.title}</h3>
      
      <div className="image-carousel">
        {university.images && university.images.length > 0 ? (
          <>
            <div className="carousel-image-container">
              <img 
                src={university.images[currentImageIndex]} 
                alt={`${university.title} - image ${currentImageIndex + 1}`} 
                className="carousel-image"
              />
            </div>
            
            {university.images.length > 1 && (
              <>
                <button className="carousel-button prev" onClick={prevImage}>&#10094;</button>
                <button className="carousel-button next" onClick={nextImage}>&#10095;</button>
                <div className="carousel-dots">
                  {university.images.map((_, index) => (
                    <span 
                      key={index} 
                      className={`carousel-dot ${index === currentImageIndex ? 'active' : ''}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setCurrentImageIndex(index);
                      }}
                    />
                  ))}
                </div>
              </>
            )}
          </>
        ) : (
          <div className="placeholder-image">
            <span>No Images Available</span>
          </div>
        )}
      </div>
      
      <div className="university-details">
        <div className="university-stats">
          <div className="stat">
            <span className="stat-icon">🏆</span>
            <span className="stat-label">Ranking</span>
            <span className="stat-value">#{university.ranking}</span>
          </div>
          <div className="stat">
            <span className="stat-icon">👨‍🎓</span>
            <span className="stat-label">Students</span>
            <span className="stat-value">{university.student_count.toLocaleString()}</span>
          </div>
          <div className="stat">
            <span className="stat-icon">📊</span>
            <span className="stat-label">Min GPA</span>
            <span className="stat-value">{university.gpa.toFixed(1)}</span>
          </div>
        </div>
        
        <p className="university-description">{truncateDescription(university.description)}</p>
        
        <div className="university-meta">
          <div className="meta-item">
            <span className="meta-label">Terms</span>
            <div className="terms-list">
              {university.terms.map((term, index) => (
                <span key={index} className="term-badge">{term}</span>
              ))}
            </div>
          </div>
          
          <div className="meta-item">
            <span className="meta-label">Language</span>
            <span className="meta-value">{university.language}</span>
          </div>
          
          <div className="meta-item costs">
            <span className="meta-label">Costs</span>
            <span className="costs-value">{formattedCosts}</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default UniversityCard; 