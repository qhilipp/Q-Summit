import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Welcome from '../Welcome/Welcome.jsx';
import UniversityInfo from '../UniversityInfo/UniversityInfo.jsx';
import GpaInfo from '../GpaInfo/GpaInfo.jsx';
import LanguagesInfo from '../LanguagesInfo/LanguagesInfo.jsx';
import BudgetInfo from '../BudgetInfo/BudgetInfo.jsx';
import TravelMonthsInfo from '../TravelMonthsInfo/TravelMonthsInfo.jsx';
import ResultsPage from '../ResultsPage/ResultsPage.jsx';
import UniversityPage from '../UniversityPage/UniversityPage.jsx';
import './App.css';

// Main application component - updated for hot reload test
function App() {
  console.log('App component rendered - Hot reload test is working!');
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Welcome />} />
        <Route path="/university" element={<UniversityInfo />} />
        <Route path="/gpa" element={<GpaInfo />} />
        <Route path="/languages" element={<LanguagesInfo />} />
        <Route path="/budget" element={<BudgetInfo />} />
        <Route path="/travel-months" element={<TravelMonthsInfo />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/university/:id" element={<UniversityPage />} />
      </Routes>
    </Router>
  );
}

export default App;
