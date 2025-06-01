import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Map from './pages/Map';

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Map />} />
      </Routes>
    </Router>
  );
};

export default App;
