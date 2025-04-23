import { motion } from 'framer-motion';
import './Button.css';

const Button = ({ children, onClick, className = '' }) => {
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
    <motion.button
      className={`welcome-button ${className}`}
      variants={buttonVariants}
      whileHover="hover"
      onClick={onClick}
    >
      {children}
    </motion.button>
  );
};

export default Button; 