import React, { useState, useEffect, useRef } from 'react';
import {
  Plus,
  Search,
  MapPin,
  DollarSign,
  Briefcase,
  Eye,
  Clock,
  Star,
  Calendar,
  Loader,
  RefreshCw,
  Upload,
  FileText,
  Send,
  CheckCircle,
  X,
  Download,
  Users,
  Mail,
  Phone,
  Filter,
  SortAsc,
  SortDesc,
  UserCheck,
  Target,
  TrendingUp,
  Award,
  Zap,
  FileSearch,
  Tag,
  Activity,
  BarChart3,
  History,
  Database,
  Wifi,
  AlertCircle,
  Brain,
  Sparkles,
  Settings,
  Play,
  Pause,
  CheckSquare,
  Shield
} from 'lucide-react';


// API Configuration
const API_CONFIG = {
  BASE_URL: 'https://findings-garden-peer-gained.trycloudflare.com',
  API_KEY: 'sk-hiring-bot-2024-secret-key-xyz789',
  DEMO_MODE: false
};

const CareerPortal = ({ userRole = 'hr' }) => {
  // Basic states
  const [apiJobs, setApiJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [showJobForm, setShowJobForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedJob, setSelectedJob] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [showApplicationForm, setShowApplicationForm] = useState(false);
  const [applicationJob, setApplicationJob] = useState(null);
  const [applicationStatus, setApplicationStatus] = useState(null);

  // HR-specific states
  const [showHRDashboard, setShowHRDashboard] = useState(false);
  const [selectedJobApplications, setSelectedJobApplications] = useState(null);
  const [jobApplications, setJobApplications] = useState({});
  const [loadingApplications, setLoadingApplications] = useState(false);
  const [sortBy, setSortBy] = useState('date');
  const [sortOrder, setSortOrder] = useState('desc');

  // Enhanced Resume filtering states
  const [topResumes, setTopResumes] = useState({});
  const [loadingTopResumes, setLoadingTopResumes] = useState(false);
  const [filteringStatus, setFilteringStatus] = useState({});
  const [filteringReport, setFilteringReport] = useState({});
  const [showTopResumes, setShowTopResumes] = useState(false);
  const [loadingFilteringReport, setLoadingFilteringReport] = useState(false);
  const [filteringProgress, setFilteringProgress] = useState({});
  const [aiAnalysisResults, setAiAnalysisResults] = useState({});

  // Advanced filtering states
  const [availableLocations, setAvailableLocations] = useState([]);
  const [availableSkills, setAvailableSkills] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState('');
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loadingSearch, setLoadingSearch] = useState(false);

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [sortField, setSortField] = useState('created_at');
  const [sortDirection, setSortDirection] = useState('desc');
  const [totalJobs, setTotalJobs] = useState(0);

  // Health monitoring
  const [healthStatus, setHealthStatus] = useState(null);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [jobHistory, setJobHistory] = useState({});
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Resume viewer states
  const [showResumeViewer, setShowResumeViewer] = useState(false);
  const [currentResume, setCurrentResume] = useState(null);
  const [resumeLoading, setResumeLoading] = useState(false);

  // Confirmation dialog state
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState({
    title: '',
    message: '',
    onConfirm: null,
    onCancel: null
  });

  // Refs
  const fetchingJobs = useRef(false);
  const fetchingStats = useRef(false);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);
  const pollIntervalRef = useRef(null);

  // Enhanced API calls with better error handling
  const makeAPICall = async (endpoint, options = {}) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, {
        method: 'GET',
        headers: {
          'X-API-Key': API_CONFIG.API_KEY,
          'ngrok-skip-browser-warning': 'true',
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          ...options.headers
        },
        signal: controller.signal,
        ...options
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
      }

      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      throw err;
    }
  };

  // Show confirmation dialog
  const showConfirmation = (title, message, onConfirm) => {
    setConfirmDialog({
      title,
      message,
      onConfirm: () => {
        onConfirm();
        setShowConfirmDialog(false);
      },
      onCancel: () => setShowConfirmDialog(false)
    });
    setShowConfirmDialog(true);
  };

  // Check API health
  const checkHealth = async () => {
    try {
      const data = await makeAPICall('/api/health');
      setHealthStatus(data);
    } catch (err) {
      setHealthStatus({ status: 'error', message: err.message });
    }
  };

  // Enhanced job fetching
  const fetchJobs = async (isManualRefresh = false) => {
    if (fetchingJobs.current && !isManualRefresh) {
      return;
    }

    try {
      fetchingJobs.current = true;
      setLoading(true);
      if (isManualRefresh) setError(null);

      const params = new URLSearchParams({
        page: currentPage.toString(),
        per_page: perPage.toString(),
        sort: sortField,
        order: sortDirection
      });

      if (selectedLocation) params.append('location', selectedLocation);
      if (selectedSkills.length > 0) params.append('skills', selectedSkills.join(','));

      const data = await makeAPICall(`/api/jobs/approved?${params}`);

      if (data.success && data.data && data.data.jobs) {
        setApiJobs(data.data.jobs);
        setTotalJobs(data.data.total || data.data.jobs.length);
        setLastUpdated(new Date());
        setError(null);
      } else {
        setApiJobs([]);
        setError('No jobs found in API response');
      }
    } catch (err) {
      if (isManualRefresh || apiJobs.length === 0) {
        setError(err.message);
      }
      if (!isManualRefresh && apiJobs.length === 0) {
        setApiJobs([]);
      }
    } finally {
      fetchingJobs.current = false;
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  };

  // Fetch statistics
  const fetchStats = async () => {
    try {
      const data = await makeAPICall('/api/stats');
      if (data.success && data.data && data.data.overall) {
        setStats(data.data.overall);
      }
    } catch (err) {
      // Stats fetch failed silently
    }
  };

  // Fetch locations and skills
  const fetchLocations = async () => {
    try {
      const data = await makeAPICall('/api/locations');
      setAvailableLocations(data.success ? data.data || [] : Array.isArray(data) ? data : []);
    } catch (err) {
      setAvailableLocations([]);
    }
  };

  const fetchSkills = async () => {
    try {
      const data = await makeAPICall('/api/skills');
      setAvailableSkills(data.success ? data.data || [] : Array.isArray(data) ? data : []);
    } catch (err) {
      setAvailableSkills([]);
    }
  };

  // Advanced search
  const performAdvancedSearch = async (query) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    setLoadingSearch(true);
    try {
      const data = await makeAPICall(`/api/jobs/search?q=${encodeURIComponent(query)}`);
      if (data.success && data.data) {
        setSearchResults(data.data.jobs || []);
      }
    } catch (err) {
      // Search failed silently
    } finally {
      setLoadingSearch(false);
    }
  };

  // Enhanced filtering status with polling
  const fetchFilteringStatus = async (ticketId) => {
    try {
      const data = await makeAPICall(`/api/tickets/${ticketId}/filtering-status`);
      if (data.success) {
        const statusData = data.data;

        setFilteringStatus(prev => ({
          ...prev,
          [ticketId]: statusData
        }));

        const isRunning = statusData.status === 'running' ||
          (statusData.filtering_info && statusData.filtering_info.status === 'running') ||
          (!statusData.has_filtering_results && statusData.ready_for_filtering);

        const isCompleted = statusData.status === 'completed' ||
          (statusData.has_filtering_results && statusData.filtering_info?.status === 'completed');

        if (isRunning) {
          startFilteringPolling(ticketId);
        }

        if (isCompleted) {
          await Promise.all([
            fetchTopResumes(ticketId),
            fetchFilteringReport(ticketId)
          ]);
        }
      }
    } catch (err) {
      // Status fetch failed silently
    }
  };

  // Start polling for filtering progress
  const startFilteringPolling = (ticketId) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    pollIntervalRef.current = setInterval(async () => {
      try {
        const data = await makeAPICall(`/api/tickets/${ticketId}/filtering-status`);
        if (data.success) {
          const statusData = data.data;

          setFilteringStatus(prev => ({
            ...prev,
            [ticketId]: statusData
          }));

          const isCompleted = statusData.status === 'completed' ||
            (statusData.has_filtering_results && statusData.filtering_info?.status === 'completed') ||
            (statusData.has_filtering_results && statusData.resume_count > 0);

          const isFailed = statusData.status === 'failed' ||
            (statusData.filtering_info && statusData.filtering_info.status === 'failed');

          if (isCompleted || isFailed) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;

            if (isCompleted) {
              await Promise.all([
                fetchTopResumes(ticketId),
                fetchFilteringReport(ticketId)
              ]);
            }
          }
        }
      } catch (err) {
        // Polling failed silently
      }
    }, 2000);
  };

  // Fetch top resumes
  const fetchTopResumes = async (ticketId) => {
    setLoadingTopResumes(true);
    try {
      const data = await makeAPICall(`/api/tickets/${ticketId}/top-resumes`);

      if (data.success) {
        let topResumesList = [];

        if (data.data) {
          if (Array.isArray(data.data)) {
            topResumesList = data.data;
          } else if (data.data.top_resumes && Array.isArray(data.data.top_resumes)) {
            topResumesList = data.data.top_resumes;
          } else if (data.data.resumes && Array.isArray(data.data.resumes)) {
            topResumesList = data.data.resumes;
          } else if (data.data.filtered_resumes && Array.isArray(data.data.filtered_resumes)) {
            topResumesList = data.data.filtered_resumes;
          } else {
            const arrayProps = Object.values(data.data).filter(Array.isArray);
            if (arrayProps.length > 0) {
              topResumesList = arrayProps[0];
            }
          }
        }

        setTopResumes(prev => ({
          ...prev,
          [ticketId]: topResumesList
        }));
      } else {
        setTopResumes(prev => ({ ...prev, [ticketId]: [] }));
      }
    } catch (err) {
      setTopResumes(prev => ({ ...prev, [ticketId]: [] }));
    } finally {
      setLoadingTopResumes(false);
    }
  };

  // Enhanced filtering report fetch
  const fetchFilteringReport = async (ticketId) => {
    setLoadingFilteringReport(true);
    try {
      const data = await makeAPICall(`/api/tickets/${ticketId}/filtering-report`);

      if (data.success) {
        setFilteringReport(prev => ({
          ...prev,
          [ticketId]: data.data
        }));
      }
    } catch (err) {
      setFilteringReport(prev => ({ ...prev, [ticketId]: null }));
    } finally {
      setLoadingFilteringReport(false);
    }
  };

  // Trigger resume filtering
  const triggerResumeFiltering = async (ticketId) => {
    console.log('🚀 START AI FILTERING BUTTON CLICKED!');
    console.log('📋 Ticket ID:', ticketId);
    console.log('🌐 API URL:', `${API_CONFIG.BASE_URL}/api/tickets/${ticketId}/filter-resumes`);
    console.log('🔑 API Key:', API_CONFIG.API_KEY);

    try {
      console.log('📡 Making API call to trigger resume filtering...');

      const data = await makeAPICall(`/api/tickets/${ticketId}/filter-resumes`, {
        method: 'POST'
      });

      console.log('✅ API Response received:', data);

      if (data.success) {
        console.log('🎉 SUCCESS: AI filtering triggered successfully!');
        alert('🤖 AI Resume Filtering has been triggered! The system will analyze all resumes and rank them based on job requirements. Check back in a few minutes for results.');

        setFilteringStatus(prev => ({
          ...prev,
          [ticketId]: {
            status: 'running',
            message: 'AI analysis in progress...',
            started_at: new Date().toISOString()
          }
        }));

        console.log('🔄 Starting polling for filtering status...');
        startFilteringPolling(ticketId);

        console.log('📄 Fetching job applications...');
        await fetchJobApplications(ticketId);
      } else {
        console.error('❌ API returned error:', data.message || 'Unknown error');
        alert('Failed to trigger resume filtering: ' + (data.message || 'Unknown error'));
      }
    } catch (err) {
      console.error('💥 EXCEPTION occurred during API call:', err);
      console.error('Error details:', {
        message: err.message,
        stack: err.stack,
        name: err.name
      });
      alert('Failed to trigger resume filtering: ' + err.message);
    }
  };

  // Fetch applications for a job
  const fetchJobApplications = async (ticketId) => {
    setLoadingApplications(true);
    try {
      const data = await makeAPICall(`/api/tickets/${ticketId}/resumes`);
      if (data.success) {
        setJobApplications(prev => ({
          ...prev,
          [ticketId]: data.data.resumes || []
        }));
      }
    } catch (err) {
      setJobApplications(prev => ({ ...prev, [ticketId]: [] }));
    } finally {
      setLoadingApplications(false);
    }
  };

  // Send top resumes
  const sendTopResumes = async (ticketId) => {
    try {
      const currentTopResumes = topResumes[ticketId] || [];
      if (currentTopResumes.length === 0) {
        alert('❌ No top candidates available to send. Please run AI filtering first.');
        return;
      }

      const data = await makeAPICall(`/api/tickets/${ticketId}/send-top-resumes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ticket_id: ticketId,
          candidate_count: currentTopResumes.length
        })
      });

      if (data.success) {
        alert(`✅ Top resumes sent successfully! 
        
📧 ${currentTopResumes.length} candidate${currentTopResumes.length !== 1 ? 's' : ''} forwarded to hiring manager.
        
The best candidates based on AI analysis have been sent for review.`);
      } else {
        alert(`❌ Failed to send top resumes: ${data.message || 'Unknown error'}`);
      }
    } catch (err) {
      let errorMessage = 'Failed to send top resumes.';

      if (err.message.includes('500')) {
        errorMessage = `Server Error (500): The backend encountered an internal error.`;
      } else if (err.message.includes('404')) {
        errorMessage = 'API endpoint not found. Check if the send-top-resumes endpoint exists in your backend.';
      } else if (err.message.includes('403')) {
        errorMessage = 'Access denied. Check your API key permissions.';
      } else {
        errorMessage = `Network error: ${err.message}`;
      }

      alert(`❌ ${errorMessage}`);
    }
  };

  // Preview and download resume functions
  const previewResume = async (ticketId, filename, applicant) => {
    setResumeLoading(true);
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/tickets/${ticketId}/resumes/${filename}`, {
        method: 'GET',
        headers: {
          'X-API-Key': API_CONFIG.API_KEY,
          'ngrok-skip-browser-warning': 'true'
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to preview resume: ${response.status}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      setCurrentResume({ url, filename, applicant, type: blob.type });
      setShowResumeViewer(true);
    } catch (err) {
      alert('Failed to preview resume. Please try downloading instead.');
    } finally {
      setResumeLoading(false);
    }
  };

  const downloadResume = async (ticketId, filename) => {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/tickets/${ticketId}/resumes/${filename}`, {
        method: 'GET',
        headers: {
          'X-API-Key': API_CONFIG.API_KEY,
          'ngrok-skip-browser-warning': 'true'
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to download resume: ${response.status}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Failed to download resume. Please try again.');
    }
  };

  // Application submission
  const handleApplicationSubmit = async (formData, ticketId) => {
    try {
      const formDataToSend = new FormData();
      formDataToSend.append('resume', formData.resumeFile);
      formDataToSend.append('applicant_name', formData.name);
      formDataToSend.append('applicant_email', formData.email);
      formDataToSend.append('applicant_phone', formData.phone || '');
      formDataToSend.append('cover_letter', formData.coverLetter || '');

      const response = await fetch(`${API_CONFIG.BASE_URL}/api/tickets/${ticketId}/resumes`, {
        method: 'POST',
        headers: {
          'X-API-Key': API_CONFIG.API_KEY,
          'ngrok-skip-browser-warning': 'true'
        },
        body: formDataToSend
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        setApplicationStatus({
          type: 'success',
          message: 'Application submitted successfully! 🎉',
          applicationId: result.application_id || result.id || ticketId
        });
        return true;
      } else {
        throw new Error(result.message || 'Failed to submit application');
      }
    } catch (err) {
      throw err;
    }
  };

  // Utility functions
  const formatDate = (dateString) => {
    if (!dateString) return 'Not specified';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateString;
    }
  };

  const getDaysAgo = (dateString) => {
    if (!dateString) return '';
    try {
      const postDate = new Date(dateString);
      const now = new Date();
      const diffTime = Math.abs(now.getTime() - postDate.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      return diffDays === 1 ? '1 day ago' : `${diffDays} days ago`;
    } catch {
      return '';
    }
  };

  const getFilteringStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-100 border-green-200';
      case 'running': return 'text-blue-600 bg-blue-100 border-blue-200';
      case 'failed': return 'text-red-600 bg-red-100 border-red-200';
      default: return 'text-gray-600 bg-gray-100 border-gray-200';
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  // Component lifecycle
  useEffect(() => {
    mountedRef.current = true;

    Promise.all([
      fetchJobs(true),
      fetchStats(),
      checkHealth(),
      fetchLocations(),
      fetchSkills()
    ]);

    // Auto-refresh interval
    intervalRef.current = setInterval(() => {
      if (!error && apiJobs.length > 0) {
        fetchJobs(false);
        fetchStats();
        checkHealth();
      }
    }, 60000);

    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      fetchingJobs.current = false;
      fetchingStats.current = false;
    };
  }, []);

  // Refetch jobs when filters change
  useEffect(() => {
    if (mountedRef.current && (selectedLocation || selectedSkills.length > 0 || currentPage !== 1 || sortField !== 'created_at' || sortDirection !== 'desc')) {
      fetchJobs(true);
    }
  }, [selectedLocation, selectedSkills, currentPage, sortField, sortDirection]);

  // Event handlers
  const handleRefresh = async () => {
    setError(null);
    await Promise.all([
      fetchJobs(true),
      fetchStats(),
      checkHealth(),
      fetchLocations(),
      fetchSkills()
    ]);
  };

  const handleApplyToJob = (jobId) => {
    const job = apiJobs.find(j => j.ticket_id === jobId);
    if (job) {
      setApplicationJob(job);
      setShowApplicationForm(true);
    }
  };

  const handleViewApplications = async (job) => {
    setSelectedJobApplications(job);
    setShowHRDashboard(true);
    await Promise.all([
      fetchJobApplications(job.ticket_id),
      fetchFilteringStatus(job.ticket_id),
      fetchTopResumes(job.ticket_id)
    ]);
  };

  const handleSearchChange = (query) => {
    setSearchQuery(query);
    if (query.trim()) {
      performAdvancedSearch(query);
    } else {
      setSearchResults([]);
    }
  };

  const handleSkillToggle = (skill) => {
    setSelectedSkills(prev =>
      prev.includes(skill)
        ? prev.filter(s => s !== skill)
        : [...prev, skill]
    );
  };

  // Determine display jobs
  const displayJobs = searchQuery.trim() ? searchResults : apiJobs;
  const filteredJobs = displayJobs.filter(job =>
    job.job_title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    job.location?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    job.required_skills?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    job.employment_type?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // ENHANCED HR DASHBOARD COMPONENT
  const EnhancedHRDashboard = () => {
    const applications = jobApplications[selectedJobApplications?.ticket_id] || [];
    const topResumesList = topResumes[selectedJobApplications?.ticket_id] || [];
    const filterStatus = filteringStatus[selectedJobApplications?.ticket_id];
    const report = filteringReport[selectedJobApplications?.ticket_id];

    // Enhanced button handlers
    const handleStartFiltering = async () => {
      if (applications.length === 0) {
        alert('⚠️ No applications found to filter. Please wait for candidates to apply first.');
        return;
      }

      showConfirmation(
        '🤖 Start AI Filtering',
        `Start AI filtering for ${applications.length} application${applications.length !== 1 ? 's' : ''}?\n\nThis will analyze all resumes and rank candidates based on job requirements.`,
        () => triggerResumeFiltering(selectedJobApplications.ticket_id)
      );
    };

    const handleViewTopCandidates = () => {
      if (topResumesList.length === 0) {
        if (filterStatus?.status === 'completed') {
          alert('🤔 No top candidates found. This might indicate that no resumes met the minimum criteria, or filtering needs to be run again.');
        } else if (filterStatus?.status === 'running') {
          alert('⏳ AI filtering is still in progress. Please wait for the analysis to complete.');
        } else {
          alert('🚀 Please run AI filtering first to identify top candidates.');
        }
        return;
      }

      setShowTopResumes(!showTopResumes);
    };

    const handleSendTopResumes = async () => {
      if (topResumesList.length === 0) {
        alert('❌ No top candidates available to send. Please run AI filtering first.');
        return;
      }

      showConfirmation(
        '📧 Send Top Resumes',
        `Send ${topResumesList.length} top candidate${topResumesList.length !== 1 ? 's' : ''} to hiring manager?\n\nThis will forward the best resumes based on AI analysis.`,
        () => sendTopResumes(selectedJobApplications.ticket_id)
      );
    };

    // Calculate score statistics
    const getScoreStats = () => {
      if (topResumesList.length === 0) return null;

      const scores = topResumesList.map(resume => resume.score || 0);
      const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length;
      const maxScore = Math.max(...scores);
      const minScore = Math.min(...scores);

      return { avgScore, maxScore, minScore };
    };

    const scoreStats = getScoreStats();

    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl p-8 w-full max-w-7xl mx-4 max-h-[90vh] overflow-y-auto shadow-2xl">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h3 className="text-3xl font-bold text-gray-800 mb-2 flex items-center">
                <Brain className="w-8 h-8 mr-3 text-purple-600" />
                AI-Powered HR Dashboard
              </h3>
              <p className="text-gray-600">{selectedJobApplications?.job_title}</p>
              <p className="text-blue-600 text-sm font-medium">
                {applications.length} application{applications.length !== 1 ? 's' : ''} received
                {topResumesList.length > 0 && ` • ${topResumesList.length} top candidates identified`}
                {scoreStats && ` • Avg Score: ${(scoreStats.avgScore * 100).toFixed(1)}%`}
              </p>
            </div>
            <button
              onClick={() => {
                setShowHRDashboard(false);
                setSelectedJobApplications(null);
                setShowTopResumes(false);
              }}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* AI Resume Filtering Control Panel */}
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl p-6 mb-6 border border-purple-200">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h4 className="text-xl font-semibold text-gray-800 flex items-center">
                  <Sparkles className="w-6 h-6 mr-2 text-purple-600" />
                  AI Resume Filtering Engine
                </h4>
                <p className="text-gray-600 text-sm">Advanced AI analysis to identify the best candidates automatically</p>
                {filterStatus?.status === 'running' && (
                  <div className="mt-2 flex items-center space-x-2">
                    <div className="w-32 bg-gray-200 rounded-full h-2">
                      <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                    </div>
                    <span className="text-xs text-blue-600">Analyzing resumes...</span>
                  </div>
                )}
              </div>
              {filterStatus && (
                <div className={`px-4 py-2 rounded-full text-sm font-medium border ${getFilteringStatusColor(filterStatus.status)}`}>
                  {filterStatus.status === 'completed' && <CheckCircle className="w-4 h-4 inline mr-1" />}
                  {filterStatus.status === 'running' && <Loader className="w-4 h-4 inline mr-1 animate-spin" />}
                  {filterStatus.status === 'failed' && <AlertCircle className="w-4 h-4 inline mr-1" />}
                  Status: {filterStatus.status || 'Not started'}
                  {filterStatus.message && (
                    <div className="text-xs mt-1">{filterStatus.message}</div>
                  )}
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
              <div className="bg-white rounded-lg p-4 border shadow-sm">
                <div className="text-2xl font-bold text-blue-600">{applications.length}</div>
                <div className="text-sm text-gray-600">Total Applications</div>
              </div>
              <div className="bg-white rounded-lg p-4 border shadow-sm">
                <div className="text-2xl font-bold text-green-600">{topResumesList.length}</div>
                <div className="text-sm text-gray-600">Top Candidates</div>
              </div>
              <div className="bg-white rounded-lg p-4 border shadow-sm">
                <div className="text-2xl font-bold text-purple-600">
                  {scoreStats ? `${(scoreStats.maxScore * 100).toFixed(1)}%` : '--'}
                </div>
                <div className="text-sm text-gray-600">Best Match</div>
              </div>
              <div className="bg-white rounded-lg p-4 border shadow-sm">
                <div className="text-2xl font-bold text-orange-600">
                  {scoreStats ? `${(scoreStats.avgScore * 100).toFixed(1)}%` : '--'}
                </div>
                <div className="text-sm text-gray-600">Avg Score</div>
              </div>
            </div>

            {/* Enhanced Action Buttons */}
            <div className="flex flex-wrap gap-3">
              <button
                onClick={handleStartFiltering}
                disabled={filterStatus?.status === 'running' || applications.length === 0}
                className={`px-6 py-3 rounded-xl font-semibold flex items-center space-x-2 transition-all shadow-md ${filterStatus?.status === 'running'
                    ? 'bg-purple-400 text-white cursor-not-allowed'
                    : applications.length === 0
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-purple-600 hover:bg-purple-700 text-white hover:shadow-lg transform hover:scale-105'
                  }`}
              >
                {filterStatus?.status === 'running' ? (
                  <>
                    <Loader className="w-5 h-5 animate-spin" />
                    <span>AI Analysis Running...</span>
                  </>
                ) : (
                  <>
                    <Brain className="w-5 h-5" />
                    <span>Start AI Filtering</span>
                  </>
                )}
              </button>

              <button
                onClick={handleViewTopCandidates}
                className={`px-6 py-3 rounded-xl font-semibold flex items-center space-x-2 transition-all shadow-md ${showTopResumes
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : topResumesList.length > 0
                      ? 'bg-blue-100 hover:bg-blue-200 text-blue-800 hover:shadow-lg transform hover:scale-105'
                      : 'bg-gray-200 text-gray-500'
                  }`}
              >
                <Award className="w-5 h-5" />
                <span>
                  {showTopResumes
                    ? 'Show All Applications'
                    : `View Top Candidates (${topResumesList.length})`
                  }
                </span>
                {topResumesList.length > 0 && !showTopResumes && (
                  <span className="bg-green-500 text-white text-xs px-2 py-1 rounded-full ml-1">
                    NEW
                  </span>
                )}
              </button>

              <button
                onClick={handleSendTopResumes}
                disabled={topResumesList.length === 0}
                className={`px-6 py-3 rounded-xl font-semibold flex items-center space-x-2 transition-all shadow-md ${topResumesList.length > 0
                    ? 'bg-green-600 hover:bg-green-700 text-white hover:shadow-lg transform hover:scale-105'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }`}
              >
                <Send className="w-5 h-5" />
                <span>Send Top Resumes</span>
                {topResumesList.length > 0 && (
                  <span className="bg-white text-green-600 text-xs px-2 py-1 rounded-full ml-1 font-bold">
                    {topResumesList.length}
                  </span>
                )}
              </button>

              <button
                onClick={() => {
                  fetchJobApplications(selectedJobApplications.ticket_id);
                  fetchFilteringStatus(selectedJobApplications.ticket_id);
                  fetchTopResumes(selectedJobApplications.ticket_id);
                }}
                disabled={loadingApplications}
                className="bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 text-white px-6 py-3 rounded-xl font-semibold flex items-center space-x-2 transition-colors shadow-md"
              >
                <RefreshCw className={`w-5 h-5 ${loadingApplications ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>
            </div>

            {/* Enhanced Filtering Report Summary */}
            {report && (
              <div className="mt-4 p-4 bg-white rounded-lg border border-orange-200 shadow-sm">
                <h5 className="font-semibold text-gray-800 mb-3 flex items-center">
                  <BarChart3 className="w-5 h-5 mr-2 text-orange-600" />
                  AI Analysis Report
                </h5>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-700">
                  <div>
                    <p><strong>Analysis completed:</strong> {formatDate(report.completed_at)}</p>
                    {report.analysis_summary && (
                      <>
                        <p><strong>Resumes analyzed:</strong> {report.analysis_summary.total_resumes}</p>
                        <p><strong>Top candidates found:</strong> {report.analysis_summary.top_candidates}</p>
                      </>
                    )}
                  </div>
                  <div>
                    {report.analysis_summary && (
                      <>
                        <p><strong>Average match score:</strong> {(report.analysis_summary.average_score * 100).toFixed(1)}%</p>
                        <p><strong>Processing time:</strong> {report.processing_time || 'N/A'}</p>
                        <p><strong>AI Model:</strong> {report.model_version || 'Latest'}</p>
                      </>
                    )}
                  </div>
                </div>
                {report.insights && (
                  <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                    <p className="text-sm text-blue-800"><strong>📊 Key Insights:</strong> {report.insights}</p>
                  </div>
                )}
              </div>
            )}

            {/* Score Distribution Chart */}
            {scoreStats && topResumesList.length > 0 && (
              <div className="mt-4 p-4 bg-white rounded-lg border border-green-200 shadow-sm">
                <h5 className="font-semibold text-gray-800 mb-3 flex items-center">
                  <TrendingUp className="w-5 h-5 mr-2 text-green-600" />
                  Score Distribution
                </h5>
                <div className="flex items-center space-x-6">
                  <div className="text-center">
                    <div className="text-lg font-bold text-green-600">{(scoreStats.maxScore * 100).toFixed(1)}%</div>
                    <div className="text-xs text-gray-600">Highest</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-blue-600">{(scoreStats.avgScore * 100).toFixed(1)}%</div>
                    <div className="text-xs text-gray-600">Average</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-orange-600">{(scoreStats.minScore * 100).toFixed(1)}%</div>
                    <div className="text-xs text-gray-600">Lowest</div>
                  </div>
                  <div className="flex-1">
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className="bg-gradient-to-r from-red-400 via-yellow-400 to-green-500 h-3 rounded-full"
                        style={{ width: `${scoreStats.avgScore * 100}%` }}
                      ></div>
                    </div>
                    <div className="text-xs text-gray-600 mt-1">Overall Performance</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Applications List */}
          {loadingApplications ? (
            <div className="text-center py-12">
              <Loader className="w-8 h-8 animate-spin mx-auto text-blue-600" />
              <p className="text-gray-600 mt-4">Loading applications...</p>
            </div>
          ) : (showTopResumes ? topResumesList : applications).length === 0 ? (
            <div className="text-center py-12">
              <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h4 className="text-lg font-semibold text-gray-600 mb-2">
                {showTopResumes ? 'No Top Candidates Yet' : 'No Applications Yet'}
              </h4>
              <p className="text-gray-500">
                {showTopResumes
                  ? 'Run AI filtering to identify the best candidates for this position.'
                  : 'Applications will appear here when candidates apply for this position.'
                }
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {(showTopResumes ? topResumesList : applications).map((application, index) => {
                // Enhanced score field detection for backend structure
                let score = null;
                let detailedScores = {};

                if (application.scores) {
                  const overallScore = application.scores.overall;

                  if (overallScore && typeof overallScore === 'string') {
                    const cleanScore = overallScore.replace('%', '').trim();
                    const numericScore = parseFloat(cleanScore);

                    if (!isNaN(numericScore)) {
                      score = numericScore / 100;
                    }
                  } else if (typeof overallScore === 'number') {
                    score = overallScore > 1 ? overallScore / 100 : overallScore;
                  }

                  // Capture ALL available score fields dynamically
                  detailedScores = { ...application.scores };

                  // Remove overall from detailed view since it's shown separately
                  delete detailedScores.overall;

                } else {
                  const rawScore = application.score || application.match_score || application.similarity_score ||
                    application.ranking_score || application.ai_score || application.overall_score ||
                    application.total_score || application.final_score || application.percentage ||
                    application.match_percentage || application.compatibility_score;

                  if (rawScore !== undefined && rawScore !== null) {
                    const numScore = parseFloat(rawScore);
                    if (!isNaN(numScore)) {
                      score = numScore > 1 ? numScore / 100 : numScore;
                    }
                  }

                  // Try to extract any other score-related fields
                  Object.keys(application).forEach(key => {
                    if (key.includes('score') || key.includes('match') || key.includes('rating') ||
                      key.includes('percentage') || key.includes('rank')) {
                      const value = application[key];
                      if (value !== undefined && value !== null && key !== 'score' && key !== 'overall_score') {
                        detailedScores[key] = value;
                      }
                    }
                  });
                }

                const hasScore = score !== null && score !== undefined && !isNaN(score);
                const scorePercentage = hasScore ? (score * 100).toFixed(1) : '0';

                return (
                  <div key={index} className={`rounded-xl p-6 border hover:shadow-md transition-shadow ${showTopResumes ? 'bg-gradient-to-r from-blue-50 to-green-50 border-blue-200' : 'bg-gray-50 border-gray-200'
                    }`}>
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <UserCheck className="w-5 h-5 text-blue-600" />
                          <h4 className="text-lg font-semibold text-gray-800">
                            {application.applicant_name || application.name || 'Unknown Applicant'}
                          </h4>
                          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">
                            {formatDate(application.uploaded_at || application.upload_date || application.created_at)}
                          </span>

                          {/* Rank Badge */}
                          {application.rank && (
                            <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded-full text-xs font-bold">
                              #{application.rank}
                            </span>
                          )}

                          {/* Experience Badge */}
                          {application.experience_years && (
                            <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">
                              {application.experience_years} years exp
                            </span>
                          )}

                          {(showTopResumes || hasScore) && hasScore && (
                            <div className="flex items-center space-x-2">
                              <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-bold flex items-center border border-green-300">
                                <Star className="w-4 h-4 mr-1 text-yellow-500" />
                                {scorePercentage}% Match
                              </span>
                              {score >= 0.8 && (
                                <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs font-bold">
                                  🏆 TOP TIER
                                </span>
                              )}
                              {score >= 0.6 && score < 0.8 && (
                                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-bold">
                                  ⭐ STRONG
                                </span>
                              )}
                              {score < 0.6 && score >= 0.4 && (
                                <span className="bg-orange-100 text-orange-800 px-2 py-1 rounded-full text-xs font-bold">
                                  🔶 GOOD
                                </span>
                              )}
                              {score < 0.4 && (
                                <span className="bg-gray-100 text-gray-800 px-2 py-1 rounded-full text-xs font-bold">
                                  📋 POTENTIAL
                                </span>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Enhanced Score Display */}
                        {hasScore && (
                          <div className="mb-4 p-4 bg-white rounded-lg border border-green-200 shadow-sm">
                            <div className="flex items-center justify-between mb-3">
                              <span className="text-sm font-semibold text-gray-700 flex items-center">
                                <Brain className="w-4 h-4 mr-1 text-purple-600" />
                                AI Match Score
                              </span>
                              <div className="text-right">
                                <span className="text-xl font-bold text-green-600">{scorePercentage}%</span>
                                <div className="text-xs text-gray-500">Overall Match</div>
                              </div>
                            </div>

                            {/* Score Progress Bar */}
                            <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
                              <div
                                className={`h-3 rounded-full transition-all duration-500 ${score >= 0.8 ? 'bg-gradient-to-r from-green-400 to-green-600' :
                                    score >= 0.6 ? 'bg-gradient-to-r from-blue-400 to-blue-600' :
                                      score >= 0.4 ? 'bg-gradient-to-r from-orange-400 to-orange-600' :
                                        'bg-gradient-to-r from-red-400 to-red-600'
                                  }`}
                                style={{ width: `${score * 100}%` }}
                              ></div>
                            </div>

                            <div className="flex justify-between text-xs text-gray-500 mb-3">
                              <span>0%</span>
                              <span className="font-medium">Perfect Match</span>
                              <span>100%</span>
                            </div>

                            {/* Enhanced Detailed Score Breakdown - Dynamic Fields */}
                            {Object.keys(detailedScores).filter(key => detailedScores[key] && detailedScores[key] !== 'N/A').length > 0 && (
                              <div className="mt-3 pt-3 border-t border-gray-100">
                                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                                  {Object.entries(detailedScores)
                                    .filter(([key, value]) => value && value !== 'N/A' && key !== 'overall')
                                    .map(([key, value], index) => {
                                      // Color mapping for different score types
                                      const getScoreColor = (scoreKey, index) => {
                                        const colorMap = {
                                          'skills': 'text-blue-600',
                                          'experience': 'text-purple-600',
                                          'location': 'text-orange-600',
                                          'education': 'text-green-600',
                                          'certifications': 'text-teal-600',
                                          'keywords': 'text-indigo-600',
                                          'relevance': 'text-pink-600',
                                          'quality': 'text-red-600',
                                          'formatting': 'text-gray-600',
                                          'completeness': 'text-yellow-600'
                                        };
                                        return colorMap[scoreKey.toLowerCase()] ||
                                          ['text-blue-600', 'text-green-600', 'text-purple-600', 'text-orange-600'][index % 4];
                                      };

                                      const formatScoreKey = (key) => {
                                        return key.split('_')
                                          .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                                          .join(' ');
                                      };

                                      return (
                                        <div key={key} className="text-center bg-white rounded-lg p-2 border border-gray-100 shadow-sm">
                                          <div className={`text-sm font-bold ${getScoreColor(key, index)}`}>
                                            {value}
                                          </div>
                                          <div className="text-xs text-gray-500 truncate" title={formatScoreKey(key)}>
                                            {formatScoreKey(key)}
                                          </div>
                                        </div>
                                      );
                                    })}
                                </div>
                              </div>
                            )}

                            <div className="mt-2 text-xs text-gray-400 text-center">
                              Score provided by AI Resume Analysis Engine
                            </div>
                          </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                          {(application.applicant_email || application.email) && (
                            <div className="flex items-center space-x-2">
                              <Mail className="w-4 h-4 text-gray-500" />
                              <span className="text-gray-700">{application.applicant_email || application.email}</span>
                            </div>
                          )}
                          {application.experience_years && (
                            <div className="flex items-center space-x-2">
                              <Briefcase className="w-4 h-4 text-gray-500" />
                              <span className="text-gray-700">{application.experience_years} years experience</span>
                            </div>
                          )}
                        </div>

                        {(application.cover_letter || application.notes) && (
                          <div className="mb-4 p-3 bg-white rounded-lg border shadow-sm">
                            <h5 className="font-medium text-gray-800 mb-2">Motivation:</h5>
                            <p className="text-gray-700 text-sm">{application.cover_letter || application.notes}</p>
                          </div>
                        )}

                        {/* Enhanced Skills Display */}
                        {(application.matched_skills || application.missing_skills) && (
                          <div className="mb-4 p-4 bg-white rounded-lg border border-green-200 shadow-sm">
                            <h5 className="font-medium text-gray-800 mb-2 flex items-center">
                              <Target className="w-4 h-4 mr-1 text-green-600" />
                              Skills Analysis
                            </h5>

                            {/* Matched Skills */}
                            {application.matched_skills && application.matched_skills.length > 0 && (
                              <div className="mb-3">
                                <h6 className="text-sm font-medium text-gray-700 mb-2">
                                  ✅ Matched Skills ({application.matched_skills.length}):
                                </h6>
                                <div className="flex flex-wrap gap-1">
                                  {application.matched_skills.map((skill, skillIndex) => (
                                    <span key={skillIndex} className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">
                                      ✓ {skill}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Missing Skills */}
                            {application.missing_skills && application.missing_skills.length > 0 && (
                              <div className="mb-3">
                                <h6 className="text-sm font-medium text-gray-700 mb-2">
                                  📈 Areas for Development ({application.missing_skills.length}):
                                </h6>
                                <div className="flex flex-wrap gap-1">
                                  {application.missing_skills.map((skill, skillIndex) => (
                                    <span key={skillIndex} className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs font-medium">
                                      ○ {skill}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Skills Summary */}
                            {application.skill_match_ratio && (
                              <div className="p-2 bg-blue-50 rounded text-center">
                                <span className="text-sm font-semibold text-blue-800">
                                  Skills Match: {application.skill_match_ratio} • Score: {detailedScores.skills || 'N/A'}
                                </span>
                              </div>
                            )}
                          </div>
                        )}

                        {(showTopResumes || hasScore) && (application.analysis || application.ai_analysis || application.reasoning ||
                          application.summary || application.ai_summary || application.evaluation || application.assessment ||
                          application.feedback || application.comments || application.notes || application.description) && (
                            <div className="mb-4 p-4 bg-white rounded-lg border border-purple-200 shadow-sm">
                              <h5 className="font-medium text-gray-800 mb-2 flex items-center">
                                <Brain className="w-4 h-4 mr-1 text-purple-600" />
                                AI Analysis & Recommendations:
                              </h5>

                              {/* Main AI Analysis */}
                              <div className="text-gray-700 text-sm leading-relaxed bg-purple-50 p-3 rounded-lg mb-3">
                                <p>{application.analysis || application.ai_analysis || application.reasoning ||
                                  application.summary || application.ai_summary || application.evaluation ||
                                  application.assessment || application.feedback || application.comments ||
                                  application.notes || application.description}</p>
                              </div>

                              {/* Additional AI fields if available */}
                              <div className="space-y-2">
                                {/* AI Recommendation */}
                                {application.recommendation && (
                                  <div className="p-2 bg-blue-50 rounded-lg border border-blue-200">
                                    <h6 className="text-sm font-medium text-blue-800 mb-1 flex items-center">
                                      <Target className="w-3 h-3 mr-1" />
                                      AI Recommendation:
                                    </h6>
                                    <p className="text-sm text-blue-700">{application.recommendation}</p>
                                  </div>
                                )}

                                {/* Strengths */}
                                {(application.strengths || application.positive_points) && (
                                  <div className="p-2 bg-green-50 rounded-lg border border-green-200">
                                    <h6 className="text-sm font-medium text-green-800 mb-1 flex items-center">
                                      <CheckCircle className="w-3 h-3 mr-1" />
                                      Key Strengths:
                                    </h6>
                                    <p className="text-sm text-green-700">{application.strengths || application.positive_points}</p>
                                  </div>
                                )}

                                {/* Areas for Improvement */}
                                {(application.weaknesses || application.areas_for_improvement || application.concerns) && (
                                  <div className="p-2 bg-orange-50 rounded-lg border border-orange-200">
                                    <h6 className="text-sm font-medium text-orange-800 mb-1 flex items-center">
                                      <AlertCircle className="w-3 h-3 mr-1" />
                                      Areas for Development:
                                    </h6>
                                    <p className="text-sm text-orange-700">{application.weaknesses || application.areas_for_improvement || application.concerns}</p>
                                  </div>
                                )}

                                {/* Interview Questions */}
                                {application.interview_questions && (
                                  <div className="p-2 bg-indigo-50 rounded-lg border border-indigo-200">
                                    <h6 className="text-sm font-medium text-indigo-800 mb-1 flex items-center">
                                      <Activity className="w-3 h-3 mr-1" />
                                      Suggested Interview Questions:
                                    </h6>
                                    <p className="text-sm text-indigo-700">{application.interview_questions}</p>
                                  </div>
                                )}

                                {/* Fit Score */}
                                {application.fit_score && (
                                  <div className="p-2 bg-teal-50 rounded-lg border border-teal-200">
                                    <h6 className="text-sm font-medium text-teal-800 mb-1 flex items-center">
                                      <Award className="w-3 h-3 mr-1" />
                                      Cultural Fit Score:
                                    </h6>
                                    <p className="text-sm text-teal-700">{application.fit_score}</p>
                                  </div>
                                )}
                              </div>

                              {/* Confidence Level */}
                              {application.confidence_level && (
                                <div className="mt-3 pt-2 border-t border-purple-100">
                                  <div className="flex justify-between items-center text-xs">
                                    <span className="text-gray-500">AI Confidence Level:</span>
                                    <span className="font-medium text-purple-600">{application.confidence_level}</span>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                      </div>
                    </div>

                    <div className="flex justify-between items-center">
                      <div className="flex items-center space-x-4">
                        <div className="flex items-center space-x-2">
                          <FileText className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-600">{application.filename || application.file_name}</span>
                        </div>
                        <div className="text-sm text-gray-500">
                          {formatFileSize(application.file_size)}
                        </div>
                        {showTopResumes && application.rank && (
                          <div className="text-sm text-purple-600 font-medium flex items-center">
                            <Award className="w-3 h-3 mr-1" />
                            Rank #{application.rank}
                          </div>
                        )}
                      </div>
                      <div className="flex space-x-2">
                        <button
                          onClick={() => previewResume(selectedJobApplications.ticket_id, application.filename || application.file_name, application)}
                          disabled={resumeLoading}
                          className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-3 py-2 rounded-lg font-medium flex items-center space-x-1 transition-colors text-sm shadow-sm"
                        >
                          {resumeLoading ? (
                            <Loader className="w-4 h-4 animate-spin" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                          <span>Preview</span>
                        </button>
                        <button
                          onClick={() => downloadResume(selectedJobApplications.ticket_id, application.filename || application.file_name)}
                          className="bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded-lg font-medium flex items-center space-x-1 transition-colors text-sm shadow-sm"
                        >
                          <Download className="w-4 h-4" />
                          <span>Download</span>
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  };
  // Add this component inside your CareerPortal.js file, before the ApplicationForm component

const TextCaptcha = ({ onVerify, onError }) => {
  const [captchaData, setCaptchaData] = useState(null);
  const [userInput, setUserInput] = useState('');
  const [isVerified, setIsVerified] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Generate new CAPTCHA
  const generateCaptcha = async () => {
    setLoading(true);
    setError('');
    setUserInput('');
    setIsVerified(false);

    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/captcha/generate`, {
        method: 'GET',
        headers: {
          'ngrok-skip-browser-warning': 'true',
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to generate CAPTCHA');
      }

      const result = await response.json();
      if (result.success) {
        setCaptchaData(result.data);
      } else {
        throw new Error(result.error || 'Failed to generate CAPTCHA');
      }
    } catch (err) {
      setError('Failed to load CAPTCHA. Please try again.');
      if (onError) onError(err);
    } finally {
      setLoading(false);
    }
  };

  // Load CAPTCHA on mount
  useEffect(() => {
    generateCaptcha();
  }, []);

  // Verify CAPTCHA
  const handleVerify = async () => {
    if (!userInput.trim()) {
      setError('Please enter the CAPTCHA text');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/captcha/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({
          session_id: captchaData.session_id,
          captcha_text: userInput
        })
      });

      const result = await response.json();
      
      if (result.success) {
        setIsVerified(true);
        setError('');
        if (onVerify) {
          onVerify(true, captchaData.session_id, userInput);
        }
      } else {
        setError(result.message || 'Incorrect CAPTCHA. Please try again.');
        generateCaptcha(); // Generate new CAPTCHA on failure
      }
    } catch (err) {
      setError('Failed to verify CAPTCHA. Please try again.');
      generateCaptcha();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-semibold text-gray-800 flex items-center">
          <Shield className="w-5 h-5 mr-2 text-purple-600" />
          Security Verification
        </h4>
        <button
          onClick={generateCaptcha}
          disabled={loading}
          className="text-purple-600 hover:text-purple-700 disabled:text-purple-400"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>
      
      {!isVerified ? (
        <>
          {/* CAPTCHA Image */}
          <div className="bg-white rounded-lg p-2 mb-3 text-center">
            {captchaData ? (
              <img 
                src={captchaData.image} 
                alt="CAPTCHA" 
                className="mx-auto"
                style={{ imageRendering: 'crisp-edges' }}
              />
            ) : (
              <div className="h-20 flex items-center justify-center">
                <Loader className="w-6 h-6 animate-spin text-purple-600" />
              </div>
            )}
          </div>
          
          {/* Input and Verify Button */}
          <div className="flex space-x-2">
            <input
              type="text"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value.toUpperCase())}
              placeholder="Enter the text above"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              onKeyPress={(e) => e.key === 'Enter' && handleVerify()}
              disabled={loading || !captchaData}
              maxLength={8}
            />
            <button
              onClick={handleVerify}
              disabled={loading || !captchaData}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-purple-400"
            >
              {loading ? (
                <Loader className="w-5 h-5 animate-spin" />
              ) : (
                'Verify'
              )}
            </button>
          </div>
          
          {/* Error Message */}
          {error && (
            <p className="text-red-600 text-sm mt-2">{error}</p>
          )}
          
          {/* Help Text */}
          <p className="text-xs text-gray-500 mt-2">
            Type the characters you see in the image above. Letters are not case-sensitive.
          </p>
        </>
      ) : (
        <div className="flex items-center text-green-600">
          <CheckCircle className="w-5 h-5 mr-2" />
          <span className="font-medium">Verified successfully!</span>
        </div>
      )}
    </div>
  );
};

  // APPLICATION FORM COMPONENT
  // Replace your existing ApplicationForm component with this updated version

const ApplicationForm = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    coverLetter: '',
    resumeFile: null
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  
  // CAPTCHA states
  const [captchaVerified, setCaptchaVerified] = useState(false);
  const [captchaSession, setCaptchaSession] = useState(null);
  const [captchaText, setCaptchaText] = useState(null);
  const [showCaptcha, setShowCaptcha] = useState(false);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      if (!allowedTypes.includes(file.type)) {
        setSubmitError('Please upload a PDF or Word document');
        return;
      }

      if (file.size > 5 * 1024 * 1024) {
        setSubmitError('File size must be less than 5MB');
        return;
      }

      setFormData({ ...formData, resumeFile: file });
      setSubmitError(null);
      
      // Show CAPTCHA when form is complete
      if (formData.name && formData.email) {
        setShowCaptcha(true);
      }
    }
  };

  const handleCaptchaVerify = (verified, sessionId, text) => {
    setCaptchaVerified(verified);
    setCaptchaSession(sessionId);
    setCaptchaText(text);
    setSubmitError(null);
  };

  const handleCaptchaError = (error) => {
    console.error('CAPTCHA error:', error);
    setCaptchaVerified(false);
  };

  const handleSubmit = async () => {
    if (!formData.name || !formData.email || !formData.resumeFile) {
      setSubmitError('Please fill in all required fields and upload your resume');
      return;
    }

    if (!captchaVerified) {
      setSubmitError('Please complete the CAPTCHA verification');
      setShowCaptcha(true);
      return;
    }

    setSubmitting(true);
    setSubmitError(null);

    try {
      const formDataToSend = new FormData();
      formDataToSend.append('resume', formData.resumeFile);
      formDataToSend.append('applicant_name', formData.name);
      formDataToSend.append('applicant_email', formData.email);
      formDataToSend.append('applicant_phone', formData.phone || '');
      formDataToSend.append('cover_letter', formData.coverLetter || '');
      formDataToSend.append('captcha_session', captchaSession);
      formDataToSend.append('captcha_text', captchaText);

      const response = await fetch(`${API_CONFIG.BASE_URL}/api/tickets/${applicationJob.ticket_id}/resumes`, {
        method: 'POST',
        headers: {
          'X-API-Key': API_CONFIG.API_KEY,
          'ngrok-skip-browser-warning': 'true'
        },
        body: formDataToSend
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        setApplicationStatus({
          type: 'success',
          message: 'Application submitted successfully! 🎉',
          applicationId: result.application_id || result.id || applicationJob.ticket_id
        });
        setShowApplicationForm(false);
        setFormData({ name: '', email: '', phone: '', coverLetter: '', resumeFile: null });
      } else {
        throw new Error(result.message || 'Failed to submit application');
      }
    } catch (err) {
      setSubmitError(err.message || 'Failed to submit application. Please try again.');
      // Reset CAPTCHA on error
      setCaptchaVerified(false);
      setShowCaptcha(true);
    } finally {
      setSubmitting(false);
    }
  };

  // Auto-show CAPTCHA when form is ready
  useEffect(() => {
    if (formData.name && formData.email && formData.resumeFile) {
      setShowCaptcha(true);
    }
  }, [formData.name, formData.email, formData.resumeFile]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-8 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h3 className="text-2xl font-bold text-gray-800 mb-2">Apply for Position</h3>
            <p className="text-gray-600">{applicationJob?.job_title} at {applicationJob?.location}</p>
            <p className="text-green-600 text-sm font-medium">Live Application - Real Submission</p>
          </div>
          <button
            onClick={() => setShowApplicationForm(false)}
            className="text-gray-400 hover:text-gray-600 text-2xl"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Full Name *</label>
              <input
                type="text"
                required
                placeholder="John Doe"
                className="w-full p-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email Address *</label>
              <input
                type="email"
                required
                placeholder="john@example.com"
                className="w-full p-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Phone Number</label>
            <input
              type="tel"
              placeholder="+1 (555) 123-4567"
              className="w-full p-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Resume/CV * (PDF or Word, max 5MB)
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-blue-400 transition-colors">
              <input
                type="file"
                accept=".pdf,.doc,.docx"
                onChange={handleFileChange}
                className="hidden"
                id="resume-upload"
              />
              <label htmlFor="resume-upload" className="cursor-pointer">
                <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-600">
                  {formData.resumeFile ? (
                    <span className="text-green-600 font-medium">
                      <FileText className="w-4 h-4 inline mr-1" />
                      {formData.resumeFile.name}
                    </span>
                  ) : (
                    <>Click to upload your resume or drag and drop</>
                  )}
                </p>
                <p className="text-sm text-gray-500 mt-1">PDF, DOC, DOCX up to 5MB</p>
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Motivation</label>
            <textarea
              placeholder="Tell us why you're interested in this position and what makes you a great fit..."
              className="w-full p-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
              rows={4}
              value={formData.coverLetter}
              onChange={(e) => setFormData({ ...formData, coverLetter: e.target.value })}
            />
          </div>

          {/* TEXT CAPTCHA */}
          {showCaptcha && (
            <TextCaptcha 
              onVerify={handleCaptchaVerify}
              onError={handleCaptchaError}
            />
          )}

          {submitError && (
            <div className="bg-red-100 border border-red-300 text-red-700 px-4 py-3 rounded-xl">
              {submitError}
            </div>
          )}

          <div className="flex space-x-4">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting || (showCaptcha && !captchaVerified)}
              className={`flex-1 px-6 py-3 rounded-xl font-semibold flex items-center justify-center space-x-2 transition-colors shadow-md ${
                submitting || (showCaptcha && !captchaVerified)
                  ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {submitting ? (
                <>
                  <Loader className="w-5 h-5 animate-spin" />
                  <span>Submitting Application...</span>
                </>
              ) : (
                <>
                  <Send className="w-5 h-5" />
                  <span>Submit Application</span>
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() => setShowApplicationForm(false)}
              className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 px-6 py-3 rounded-xl font-semibold transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

  // RESUME VIEWER COMPONENT
  const ResumeViewer = () => {
    const handleClose = () => {
      if (currentResume?.url) {
        window.URL.revokeObjectURL(currentResume.url);
      }
      setCurrentResume(null);
      setShowResumeViewer(false);
    };

    const handleDownload = () => {
      if (currentResume?.url) {
        const a = document.createElement('a');
        a.href = currentResume.url;
        a.download = currentResume.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }
    };

    if (!currentResume) return null;

    return (
      <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl w-full max-w-6xl mx-4 h-[90vh] flex flex-col shadow-2xl">
          <div className="flex justify-between items-center p-6 border-b border-gray-200">
            <div>
              <h3 className="text-xl font-bold text-gray-800">{currentResume.filename}</h3>
              <p className="text-gray-600">
                {currentResume.applicant?.applicant_name || 'Unknown Applicant'}
                {currentResume.applicant?.applicant_email && (
                  <span className="ml-2">({currentResume.applicant.applicant_email})</span>
                )}
              </p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleDownload}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-xl font-medium flex items-center space-x-2 transition-colors shadow-md"
              >
                <Download className="w-4 h-4" />
                <span>Download</span>
              </button>
              <button
                onClick={handleClose}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
          </div>

          <div className="flex-1 p-6">
            {currentResume.type === 'application/pdf' ? (
              <iframe
                src={currentResume.url}
                className="w-full h-full border rounded-xl"
                title={`Resume: ${currentResume.filename}`}
              />
            ) : (
              <div className="flex items-center justify-center h-full bg-gray-50 rounded-xl">
                <div className="text-center">
                  <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <h4 className="text-lg font-semibold text-gray-600 mb-2">Preview Not Available</h4>
                  <p className="text-gray-500 mb-4">
                    {currentResume.filename} cannot be previewed in the browser.
                  </p>
                  <button
                    onClick={handleDownload}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-medium flex items-center space-x-2 mx-auto transition-colors shadow-md"
                  >
                    <Download className="w-5 h-5" />
                    <span>Download to View</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // MAIN RENDER
  return (
    <div className="space-y-8 p-6 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2 flex items-center">
            {userRole === 'hr' && <Brain className="w-8 h-8 mr-3 text-purple-600" />}
            Enhanced Career Portal {userRole === 'hr' && '- AI-Powered HR Suite'}
          </h1>
          <p className="text-gray-600">
            {userRole === 'hr'
              ? '🤖 Complete hiring solution with AI resume filtering, analytics, and advanced search'
              : 'Discover opportunities with powerful search and filtering'
            }
            {lastUpdated && (
              <span className="text-sm text-gray-500 ml-2">
                Last updated: {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-xl font-medium flex items-center space-x-2 transition-colors disabled:opacity-50 shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh All</span>
          </button>
          {userRole === 'hr' && (
            <button
              onClick={() => setShowJobForm(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-semibold flex items-center space-x-2 transition-colors shadow-md"
            >
              <Plus className="w-5 h-5" />
              <span>Post Job</span>
            </button>
          )}
        </div>
      </div>

      {/* Application Status Alert */}
      {applicationStatus && (
        <div className={`p-4 rounded-xl border shadow-sm ${applicationStatus.type === 'success'
            ? 'bg-green-100 border-green-300 text-green-700'
            : 'bg-red-100 border-red-300 text-red-700'
          }`}>
          <div className="flex items-center space-x-2">
            {applicationStatus.type === 'success' && <CheckCircle className="w-5 h-5" />}
            <span className="font-medium">{applicationStatus.message}</span>
          </div>
          {applicationStatus.applicationId && (
            <p className="text-sm mt-1">Application ID: {applicationStatus.applicationId}</p>
          )}
          <button
            onClick={() => setApplicationStatus(null)}
            className="text-sm underline mt-2 hover:no-underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Health Status Dashboard */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className={`p-4 rounded-xl shadow-sm ${error
            ? 'bg-red-100 border border-red-300'
            : 'bg-green-100 border border-green-300'
          }`}>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${error ? 'bg-red-500' : 'bg-green-500'
              }`}></div>
            <span className={`font-medium ${error ? 'text-red-700' : 'text-green-700'
              }`}>
              {error ? 'API Connection Failed' : 'API Connected'}
            </span>
          </div>
          <div className={`text-sm mt-1 ${error ? 'text-red-600' : 'text-green-600'}`}>
            <p>{error || 'All systems operational'}</p>
          </div>
        </div>

        <div className={`p-4 rounded-xl shadow-sm ${healthStatus?.status === 'ok'
            ? 'bg-green-100 border border-green-300'
            : 'bg-yellow-100 border border-yellow-300'
          }`}>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${healthStatus?.status === 'ok' ? 'bg-green-500' : 'bg-yellow-500'
              }`}></div>
            <span className={`font-medium ${healthStatus?.status === 'ok' ? 'text-green-700' : 'text-yellow-700'
              }`}>
              <Database className="w-4 h-4 inline mr-1" />
              Database Status
            </span>
          </div>
          <div className={`text-sm mt-1 ${healthStatus?.status === 'ok' ? 'text-green-600' : 'text-yellow-600'
            }`}>
            <p>{healthStatus?.database || 'Checking...'}</p>
            <p className="text-xs mt-1">
              {healthStatus?.storage && `Storage: ${healthStatus.storage}`}
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-blue-100 border border-blue-300 shadow-sm">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span className="font-medium text-blue-700">
              <Wifi className="w-4 h-4 inline mr-1" />
              {userRole === 'hr' ? 'AI Engine' : 'System'} Status
            </span>
          </div>
          <div className="text-sm mt-1 text-blue-600">
            <p>{healthStatus?.tunnel || 'Active & Ready'}</p>
            <p className="text-xs mt-1">
              {userRole === 'hr' ? '🤖 AI Resume Filtering Available' : 'Application ready'}
            </p>
          </div>
        </div>
      </div>

      {/* Enhanced Statistics Dashboard */}
      {stats && (
        <div className="bg-white rounded-2xl p-6 shadow-lg">
          <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <Activity className="w-5 h-5 mr-2 text-blue-600" />
            Live Platform Analytics
            {userRole === 'hr' && <Sparkles className="w-5 h-5 ml-2 text-purple-600" />}
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="text-center p-4 bg-blue-50 rounded-xl border border-blue-100">
              <div className="text-2xl font-bold text-blue-600">{stats.total_tickets}</div>
              <div className="text-sm text-gray-600">Total Jobs</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-xl border border-green-100">
              <div className="text-2xl font-bold text-green-600">{stats.approved_jobs}</div>
              <div className="text-sm text-gray-600">Approved</div>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-xl border border-yellow-100">
              <div className="text-2xl font-bold text-yellow-600">{stats.pending_approval}</div>
              <div className="text-sm text-gray-600">Pending</div>
            </div>
            <div className="text-center p-4 bg-red-50 rounded-xl border border-red-100">
              <div className="text-2xl font-bold text-red-600">{stats.terminated_jobs}</div>
              <div className="text-sm text-gray-600">Terminated</div>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="text-center p-3 bg-blue-50 rounded-lg border border-blue-100">
              <div className="text-lg font-bold text-blue-600">{Array.isArray(availableLocations) ? availableLocations.length : 0}</div>
              <div className="text-xs text-gray-600">Active Locations</div>
            </div>
            <div className="text-center p-3 bg-green-50 rounded-lg border border-green-100">
              <div className="text-lg font-bold text-green-600">{Array.isArray(availableSkills) ? availableSkills.length : 0}</div>
              <div className="text-xs text-gray-600">Unique Skills</div>
            </div>
            <div className="text-center p-3 bg-teal-50 rounded-lg border border-teal-100">
              <div className="text-lg font-bold text-teal-600">{totalJobs}</div>
              <div className="text-xs text-gray-600">Displayed Jobs</div>
            </div>
          </div>
        </div>
      )}

      {/* Advanced Search Panel */}
      <div className="bg-white rounded-2xl p-6 shadow-lg mb-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
          <Search className="w-5 h-5 mr-2 text-blue-600" />
          Advanced Job Search & Filters
          {userRole === 'hr' && <Brain className="w-5 h-5 ml-2 text-purple-600" />}
        </h3>

        <div className="space-y-4">
          <div className="relative">
            <Search className="w-5 h-5 absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search across job titles, descriptions, skills, locations..."
              className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-sm"
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
            />
            {loadingSearch && (
              <Loader className="w-5 h-5 absolute right-4 top-1/2 transform -translate-y-1/2 text-blue-600 animate-spin" />
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <MapPin className="w-4 h-4 inline mr-1" />
                Location
              </label>
              <select
                value={selectedLocation}
                onChange={(e) => setSelectedLocation(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
              >
                <option value="">All Locations</option>
                {Array.isArray(availableLocations) && availableLocations.map(location => (
                  <option key={location} value={location}>{location}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <SortAsc className="w-4 h-4 inline mr-1" />
                Sort By
              </label>
              <select
                value={sortField}
                onChange={(e) => setSortField(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
              >
                <option value="created_at">Date Posted</option>
                <option value="approved_at">Date Approved</option>
                <option value="last_updated">Last Updated</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <TrendingUp className="w-4 h-4 inline mr-1" />
                Order
              </label>
              <select
                value={sortDirection}
                onChange={(e) => setSortDirection(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
              >
                <option value="desc">Newest First</option>
                <option value="asc">Oldest First</option>
              </select>
            </div>
          </div>

          {Array.isArray(availableSkills) && availableSkills.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Tag className="w-4 h-4 inline mr-1" />
                Skills ({selectedSkills.length} selected)
              </label>
              <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto p-2 border border-gray-200 rounded-xl bg-gray-50">
                {availableSkills.slice(0, 50).map(skill => (
                  <button
                    key={skill}
                    onClick={() => handleSkillToggle(skill)}
                    className={`px-3 py-1 rounded-full text-sm font-medium transition-colors shadow-sm ${selectedSkills.includes(skill)
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
                      }`}
                  >
                    {skill}
                  </button>
                ))}
              </div>
            </div>
          )}

          {searchQuery && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p className="text-blue-800 text-sm">
                {loadingSearch ? (
                  'Searching...'
                ) : (
                  `Found ${searchResults.length} job${searchResults.length !== 1 ? 's' : ''} matching "${searchQuery}"`
                )}
              </p>
            </div>
          )}

          {(selectedLocation || selectedSkills.length > 0) && (
            <div className="flex flex-wrap gap-2">
              <span className="text-sm text-gray-600">Active filters:</span>
              {selectedLocation && (
                <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-sm flex items-center border border-green-300">
                  <MapPin className="w-3 h-3 mr-1" />
                  {selectedLocation}
                  <button
                    onClick={() => setSelectedLocation('')}
                    className="ml-1 text-green-600 hover:text-green-800"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              )}
              {selectedSkills.map(skill => (
                <span key={skill} className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-sm flex items-center border border-blue-300">
                  <Tag className="w-3 h-3 mr-1" />
                  {skill}
                  <button
                    onClick={() => handleSkillToggle(skill)}
                    className="ml-1 text-blue-600 hover:text-blue-800"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Error State */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-center space-x-2 mb-2">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <h3 className="text-lg font-semibold text-red-800">Connection Error</h3>
          </div>
          <p className="text-red-700 mb-4">{error}</p>
          <button
            onClick={handleRefresh}
            className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-xl font-medium flex items-center space-x-2 transition-colors shadow-md"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Try Again</span>
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <Loader className="w-8 h-8 animate-spin mx-auto text-blue-600" />
          <p className="text-gray-600 mt-4">
            Loading enhanced platform features...
            {userRole === 'hr' && ' 🤖 AI systems initializing...'}
          </p>
        </div>
      )}

      {/* Jobs Grid */}
      {!loading && (
        <div className="space-y-6">
          {filteredJobs.length > 0 ? (
            <>
              {filteredJobs.map((job) => (
                <div key={job.ticket_id} className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
                  <div className="flex justify-between items-start mb-6">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-2xl font-bold text-gray-800 hover:text-blue-600 transition-colors">
                          {job.job_title || 'Unknown Position'}
                        </h3>
                        <Star className="w-5 h-5 text-yellow-400" />
                        {userRole === 'hr' && (
                          <span className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-xs font-medium flex items-center border border-purple-300">
                            <Brain className="w-3 h-3 mr-1" />
                            AI ENHANCED
                          </span>
                        )}
                        {searchQuery && (
                          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium border border-blue-300">
                            SEARCH RESULT
                          </span>
                        )}
                      </div>
                      <div className="flex items-center space-x-4 text-gray-600">
                        <div className="flex items-center space-x-1">
                          <Clock className="w-4 h-4" />
                          <span>{getDaysAgo(job.created_at) || 'Recently posted'}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Calendar className="w-4 h-4" />
                          <span>Deadline: {job.deadline || 'Not specified'}</span>
                        </div>
                      </div>
                    </div>
                    <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium border border-green-300">
                      LIVE
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    <div className="flex items-center space-x-3 p-3 bg-blue-50 rounded-xl border border-blue-100">
                      <MapPin className="w-5 h-5 text-blue-600" />
                      <span className="font-medium text-gray-700">{job.location || 'Remote'}</span>
                    </div>
                    <div className="flex items-center space-x-3 p-3 bg-green-50 rounded-xl border border-green-100">
                      <DollarSign className="w-5 h-5 text-green-600" />
                      <span className="font-medium text-gray-700">{job.salary_range || 'Competitive'}</span>
                    </div>
                    <div className="flex items-center space-x-3 p-3 bg-purple-50 rounded-xl border border-purple-100">
                      <Briefcase className="w-5 h-5 text-purple-600" />
                      <span className="font-medium text-gray-700">{job.employment_type || 'Full-time'}</span>
                    </div>
                  </div>

                  {job.experience_required && (
                    <div className="mb-4 p-3 bg-yellow-50 rounded-xl border border-yellow-100">
                      <span className="text-yellow-800 font-medium">Experience: {job.experience_required}</span>
                    </div>
                  )}

                  {job.required_skills && (
                    <div className="mb-4 p-3 bg-gray-50 rounded-xl border border-gray-200">
                      <span className="text-gray-700"><strong>Skills:</strong> {job.required_skills}</span>
                    </div>
                  )}

                  <div className="flex justify-between items-center">
                    <div className="text-sm text-gray-500">
                      Job ID: {job.ticket_id}
                    </div>
                    <div className="flex space-x-3">
                      <button
                        onClick={() => setSelectedJob(job)}
                        className="bg-gray-100 hover:bg-gray-200 text-gray-800 px-4 py-2 rounded-xl font-medium flex items-center space-x-2 transition-colors shadow-sm"
                      >
                        <Eye className="w-4 h-4" />
                        <span>View Details</span>
                      </button>
                      {userRole === 'hr' ? (
                        <button
                          onClick={() => handleViewApplications(job)}
                          className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white px-6 py-2 rounded-xl font-medium flex items-center space-x-2 transition-colors shadow-md"
                        >
                          <Brain className="w-4 h-4" />
                          <span>AI HR Dashboard</span>
                        </button>
                      ) : (
                        <button
                          onClick={() => handleApplyToJob(job.ticket_id)}
                          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl font-medium transition-colors shadow-md"
                        >
                          Apply Now
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* Pagination */}
              {Math.ceil(totalJobs / perPage) > 1 && (
                <div className="flex justify-between items-center mt-6 p-4 bg-white rounded-xl shadow-sm">
                  <div className="text-sm text-gray-600">
                    Showing {((currentPage - 1) * perPage) + 1} to {Math.min(currentPage * perPage, totalJobs)} of {totalJobs} jobs
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => setCurrentPage(currentPage - 1)}
                      disabled={currentPage === 1}
                      className="px-3 py-2 bg-gray-100 hover:bg-gray-200 disabled:opacity-50 rounded-lg text-sm transition-colors"
                    >
                      Previous
                    </button>
                    {[...Array(Math.min(5, Math.ceil(totalJobs / perPage)))].map((_, i) => {
                      const page = i + Math.max(1, currentPage - 2);
                      if (page > Math.ceil(totalJobs / perPage)) return null;
                      return (
                        <button
                          key={page}
                          onClick={() => setCurrentPage(page)}
                          className={`px-3 py-2 rounded-lg text-sm transition-colors ${page === currentPage
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-100 hover:bg-gray-200'
                            }`}
                        >
                          {page}
                        </button>
                      );
                    })}
                    <button
                      onClick={() => setCurrentPage(currentPage + 1)}
                      disabled={currentPage === Math.ceil(totalJobs / perPage)}
                      className="px-3 py-2 bg-gray-100 hover:bg-gray-200 disabled:opacity-50 rounded-lg text-sm transition-colors"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}

              <div className="text-center text-gray-600 py-4">
                Showing {filteredJobs.length} of {totalJobs} total jobs
                {searchQuery && ` (search results for "${searchQuery}")`}
                {(selectedLocation || selectedSkills.length > 0) && ' (filtered)'}
                {userRole === 'hr' && (
                  <span className="block mt-1 text-purple-600 font-medium">
                    🤖 AI Resume Filtering Available for All Positions
                  </span>
                )}
              </div>
            </>
          ) : (
            <div className="text-center py-12">
              <div className="text-gray-400 text-6xl mb-4">
                {userRole === 'hr' ? '🤖' : '💼'}
              </div>
              <h3 className="text-xl font-semibold text-gray-600 mb-2">
                {searchQuery ? 'No jobs match your search' : 'No jobs available'}
              </h3>
              <p className="text-gray-500">
                {searchQuery
                  ? 'Try adjusting your search terms or browse all available positions.'
                  : 'Jobs will appear here when your API is connected.'}
              </p>
              {!loading && (
                <button
                  onClick={handleRefresh}
                  className="mt-4 bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-xl font-medium shadow-md"
                >
                  Refresh Platform
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Job Details Modal */}
      {selectedJob && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-8 w-full max-w-3xl mx-4 max-h-[80vh] overflow-y-auto shadow-2xl">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h2 className="text-3xl font-bold text-gray-800 mb-2">{selectedJob.job_title}</h2>
                <p className="text-gray-600 text-lg">{selectedJob.location}</p>
                <p className="text-green-600 text-sm font-medium">
                  Live Job Listing {userRole === 'hr' && '• AI-Enhanced'}
                </p>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="flex items-center space-x-2 p-3 bg-blue-50 rounded-xl border border-blue-100">
                <MapPin className="w-5 h-5 text-blue-600" />
                <span className="text-gray-700">{selectedJob.location}</span>
              </div>
              <div className="flex items-center space-x-2 p-3 bg-green-50 rounded-xl border border-green-100">
                <DollarSign className="w-5 h-5 text-green-600" />
                <span className="text-gray-700">{selectedJob.salary_range}</span>
              </div>
              <div className="flex items-center space-x-2 p-3 bg-purple-50 rounded-xl border border-purple-100">
                <Briefcase className="w-5 h-5 text-purple-600" />
                <span className="text-gray-700">{selectedJob.employment_type}</span>
              </div>
            </div>

            {selectedJob.experience_required && (
              <div className="mb-4 p-3 bg-yellow-50 rounded-xl border border-yellow-100">
                <h4 className="font-semibold text-gray-800 mb-1">Experience Required</h4>
                <p className="text-gray-700">{selectedJob.experience_required}</p>
              </div>
            )}

            {selectedJob.required_skills && (
              <div className="mb-4 p-3 bg-gray-50 rounded-xl border border-gray-200">
                <h4 className="font-semibold text-gray-800 mb-1">Required Skills</h4>
                <p className="text-gray-700">{selectedJob.required_skills}</p>
              </div>
            )}

            <div className="mb-6">
              <h3 className="text-xl font-semibold mb-3 text-gray-800">Job Description</h3>
              <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
                <p className="text-gray-700 leading-relaxed">
                  {selectedJob.job_description || 'No description available for this position.'}
                </p>
              </div>
            </div>

            <div className="text-sm text-gray-500 mb-6 grid grid-cols-2 gap-4">
              <div>
                <p><strong>Posted:</strong> {formatDate(selectedJob.created_at)}</p>
                <p><strong>Approved:</strong> {formatDate(selectedJob.approved_at)}</p>
              </div>
              <div>
                <p><strong>Deadline:</strong> {selectedJob.deadline}</p>
                <p><strong>Job ID:</strong> {selectedJob.ticket_id}</p>
              </div>
            </div>

            <div className="flex space-x-4">
              {userRole === 'hr' ? (
                <button
                  onClick={() => {
                    handleViewApplications(selectedJob);
                    setSelectedJob(null);
                  }}
                  className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white px-6 py-3 rounded-xl font-semibold flex-1 transition-colors flex items-center justify-center space-x-2 shadow-md"
                >
                  <Brain className="w-5 h-5" />
                  <span>Open AI HR Dashboard</span>
                </button>
              ) : (
                <button
                  onClick={() => {
                    handleApplyToJob(selectedJob.ticket_id);
                    setSelectedJob(null);
                  }}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-semibold flex-1 transition-colors shadow-md"
                >
                  Apply for this Position
                </button>
              )}
              <button
                onClick={() => setSelectedJob(null)}
                className="bg-gray-200 hover:bg-gray-300 text-gray-800 px-6 py-3 rounded-xl font-semibold transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      {showApplicationForm && <ApplicationForm />}
      {showHRDashboard && <EnhancedHRDashboard />}
      {showResumeViewer && <ResumeViewer />}

      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
            <h3 className="text-xl font-bold text-gray-800 mb-4">{confirmDialog.title}</h3>
            <p className="text-gray-600 mb-6 whitespace-pre-line">{confirmDialog.message}</p>
            <div className="flex space-x-3">
              <button
                onClick={confirmDialog.onConfirm}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl font-semibold transition-colors shadow-md"
              >
                Confirm
              </button>
              <button
                onClick={confirmDialog.onCancel}
                className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 px-4 py-2 rounded-xl font-semibold transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CareerPortal;