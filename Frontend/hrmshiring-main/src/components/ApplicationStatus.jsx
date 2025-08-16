import React, { useState, useEffect, useRef } from 'react';
import { 
  Users, 
  Briefcase, 
  FileText, 
  CheckCircle,
  Clock,
  TrendingUp,
  Calendar,
  Award,
  BarChart3,
  ArrowUpRight,
  Plus,
  Filter,
  Search,
  MoreVertical,
  Zap,
  Loader,
  RefreshCw,
  AlertCircle,
  Target,
  Brain,
  Sparkles,
  Activity,
  MapPin,
  DollarSign,
  Eye,
  Download,
  UserCheck,
  Database,
  Wifi,
  Mail,
  Phone,
  Building,
  Star,
  TrendingDown,
  PieChart,
  BarChart,
  LineChart
} from 'lucide-react';

// API Configuration
const API_CONFIG = {
  BASE_URL: 'https://sit-obligation-missing-bare.trycloudflare.com',
  API_KEY: 'sk-hiring-bot-2024-secret-key-xyz789',
};

const FixedRealTimeAnalytics = ({ userRole = 'hr' }) => {
  // State management
  const [jobs, setJobs] = useState([]);
  const [allApplications, setAllApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedJob, setSelectedJob] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [healthStatus, setHealthStatus] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [sortBy, setSortBy] = useState('applications');
  const [filterStatus, setFilterStatus] = useState('all');
  
  // Analytics state
  const [analytics, setAnalytics] = useState({
    totalJobs: 0,
    totalApplications: 0,
    avgApplicationsPerJob: 0,
    topPerformingJobs: [],
    applicationsByStatus: {},
    applicationsByDate: [],
    jobPerformanceMetrics: []
  });

  // Refs
  const mountedRef = useRef(true);
  const intervalRef = useRef(null);

  // Enhanced API call helper
  const makeAPICall = async (endpoint, options = {}) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    try {
      console.log(`🌐 API Call: ${API_CONFIG.BASE_URL}${endpoint}`);
      
      const response = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, {
        method: 'GET',
        headers: {
          'X-API-Key': API_CONFIG.API_KEY,
          'ngrok-skip-browser-warning': 'true',
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache',
          ...options.headers
        },
        signal: controller.signal,
        ...options
      });

      clearTimeout(timeoutId);
      
      console.log(`📡 Response Status: ${response.status}`);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
      }

      const data = await response.json();
      console.log(`✅ API Success:`, data);
      return data;
      
    } catch (err) {
      clearTimeout(timeoutId);
      console.error(`❌ API Error:`, err);
      
      if (err.name === 'AbortError') {
        throw new Error('Request timeout - API took too long to respond');
      }
      
      if (err.message.includes('Failed to fetch')) {
        throw new Error('Cannot connect to API - Check if backend is running and accessible');
      }
      
      throw err;
    }
  };

  // Safe JSON parse helper
  const safeJsonParse = (jsonString, fallback = null) => {
    if (!jsonString) return fallback;
    if (typeof jsonString === 'object') return jsonString; // Already parsed
    try {
      return JSON.parse(jsonString);
    } catch (err) {
      console.warn('Failed to parse JSON:', jsonString);
      return fallback;
    }
  };

  // Safe score extraction
  const extractScore = (scoreData) => {
    if (!scoreData) return 0;
    
    // If it's already a number
    if (typeof scoreData === 'number') {
      return scoreData > 1 ? scoreData / 100 : scoreData;
    }
    
    // If it's a string percentage
    if (typeof scoreData === 'string') {
      const cleanScore = scoreData.replace('%', '').trim();
      const numScore = parseFloat(cleanScore);
      if (!isNaN(numScore)) {
        return numScore > 1 ? numScore / 100 : numScore;
      }
    }
    
    // If it's an object with overall property
    if (typeof scoreData === 'object' && scoreData.overall) {
      return extractScore(scoreData.overall);
    }
    
    return 0;
  };

  // Test API Connection
  const testAPIConnection = async () => {
    try {
      console.log('🔍 Testing API connection...');
      const healthResponse = await makeAPICall('/api/health');
      console.log('✅ Health check passed:', healthResponse);
      setHealthStatus(healthResponse);
      return true;
    } catch (error) {
      console.error('❌ API Test Failed:', error.message);
      setHealthStatus({ status: 'error', message: error.message });
      return false;
    }
  };

  // Fetch all jobs with their applications
  const fetchJobsWithApplications = async () => {
    try {
      console.log('📊 Fetching jobs and applications data...');
      
      // Fetch all approved jobs
      const jobsData = await makeAPICall('/api/jobs/approved?per_page=50');
      
      if (!jobsData.success || !jobsData.data || !jobsData.data.jobs) {
        throw new Error('No jobs data available');
      }

      const jobsList = jobsData.data.jobs;
      console.log(`📋 Found ${jobsList.length} jobs`);

      // For each job, fetch its applications (limit to first 10 jobs to avoid timeout)
      const jobsWithApplications = await Promise.all(
        jobsList.slice(0, 10).map(async (job) => {
          try {
            console.log(`🔍 Fetching applications for job: ${job.job_title} (${job.ticket_id})`);
            
            const appsData = await makeAPICall(`/api/tickets/${job.ticket_id}/resumes`);
            
            let applications = [];
            if (appsData.success && appsData.data && appsData.data.resumes) {
              applications = appsData.data.resumes.map(app => {
                // Safe data extraction
                const scores = safeJsonParse(app.scores, null);
                const matchedSkills = safeJsonParse(app.matched_skills, []);
                const missingSkills = safeJsonParse(app.missing_skills, []);
                
                return {
                  id: app.id || `${job.ticket_id}-${Date.now()}-${Math.random()}`,
                  jobId: job.ticket_id,
                  jobTitle: job.job_title,
                  candidateName: app.applicant_name || 'Unknown Candidate',
                  email: app.applicant_email || 'No email',
                  phone: app.applicant_phone || 'Not provided',
                  filename: app.filename || app.file_name || 'Resume.pdf',
                  uploadedAt: app.uploaded_at || app.created_at,
                  status: app.status || 'under_review',
                  coverLetter: app.cover_letter,
                  experienceYears: parseInt(app.experience_years) || 0,
                  scores: scores,
                  overallScore: extractScore(scores),
                  matchedSkills: Array.isArray(matchedSkills) ? matchedSkills : [],
                  missingSkills: Array.isArray(missingSkills) ? missingSkills : [],
                  analysis: app.analysis,
                  recommendation: app.recommendation,
                  rank: parseInt(app.rank) || null
                };
              });
            }

            console.log(`📊 Job "${job.job_title}" has ${applications.length} applications`);

            // Calculate job metrics
            const statusBreakdown = applications.reduce((acc, app) => {
              acc[app.status] = (acc[app.status] || 0) + 1;
              return acc;
            }, {});

            const scoresWithData = applications.filter(app => app.overallScore > 0);
            const avgScore = scoresWithData.length > 0 
              ? scoresWithData.reduce((sum, app) => sum + app.overallScore, 0) / scoresWithData.length
              : 0;

            const topCandidate = scoresWithData.length > 0 
              ? scoresWithData.sort((a, b) => b.overallScore - a.overallScore)[0]
              : applications[0] || null;

            return {
              id: job.ticket_id,
              title: job.job_title,
              description: job.job_description,
              location: job.location || 'Remote',
              salaryRange: job.salary_range || 'Competitive',
              employmentType: job.employment_type || 'Full-time',
              experienceRequired: job.experience_required,
              requiredSkills: job.required_skills,
              deadline: job.deadline,
              createdAt: job.created_at,
              approvedAt: job.approved_at,
              applications: applications,
              applicationCount: applications.length,
              statusBreakdown: statusBreakdown,
              avgScore: avgScore,
              topCandidate: topCandidate
            };
          } catch (appErr) {
            console.warn(`⚠️ Failed to fetch applications for job ${job.ticket_id}:`, appErr.message);
            return {
              id: job.ticket_id,
              title: job.job_title,
              description: job.job_description,
              location: job.location || 'Remote',
              salaryRange: job.salary_range || 'Competitive',
              employmentType: job.employment_type || 'Full-time',
              experienceRequired: job.experience_required,
              requiredSkills: job.required_skills,
              deadline: job.deadline,
              createdAt: job.created_at,
              approvedAt: job.approved_at,
              applications: [],
              applicationCount: 0,
              statusBreakdown: {},
              avgScore: 0,
              topCandidate: null
            };
          }
        })
      );

      setJobs(jobsWithApplications);
      
      // Flatten all applications for global analytics
      const allApps = jobsWithApplications.flatMap(job => job.applications);
      setAllApplications(allApps);
      
      // Calculate analytics
      calculateAnalytics(jobsWithApplications, allApps);
      
      setLastUpdated(new Date());
      setError(null);
      
      console.log(`✅ Successfully loaded ${jobsWithApplications.length} jobs with ${allApps.length} total applications`);
      
    } catch (err) {
      console.error('❌ Failed to fetch data:', err);
      setError(`Failed to fetch job data: ${err.message}`);
    }
  };

  // Calculate analytics from real data
  const calculateAnalytics = (jobsData, applicationsData) => {
    const totalJobs = jobsData.length;
    const totalApplications = applicationsData.length;
    const avgApplicationsPerJob = totalJobs > 0 ? totalApplications / totalJobs : 0;

    // Top performing jobs (by application count)
    const topPerformingJobs = jobsData
      .sort((a, b) => b.applicationCount - a.applicationCount)
      .slice(0, 5)
      .map(job => ({
        id: job.id,
        title: job.title,
        applications: job.applicationCount,
        avgScore: job.avgScore,
        location: job.location
      }));

    // Applications by status
    const applicationsByStatus = applicationsData.reduce((acc, app) => {
      acc[app.status] = (acc[app.status] || 0) + 1;
      return acc;
    }, {});

    // Applications by date (last 7 days)
    const applicationsByDate = [];
    for (let i = 6; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      
      const count = applicationsData.filter(app => {
        if (!app.uploadedAt) return false;
        const appDate = new Date(app.uploadedAt).toISOString().split('T')[0];
        return appDate === dateStr;
      }).length;
      
      applicationsByDate.push({
        date: dateStr,
        count: count,
        label: date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
      });
    }

    // Job performance metrics
    const jobPerformanceMetrics = jobsData.map(job => ({
      id: job.id,
      title: job.title,
      applications: job.applicationCount,
      avgScore: job.avgScore * 100, // Convert to percentage
      conversionRate: job.statusBreakdown.hired ? 
        (job.statusBreakdown.hired / job.applicationCount) * 100 : 0,
      qualityScore: job.avgScore > 0 ? job.avgScore * 100 : 
        (job.applicationCount > 0 ? 50 : 0),
      daysActive: job.createdAt ? 
        Math.floor((new Date() - new Date(job.createdAt)) / (1000 * 60 * 60 * 24)) : 0
    }));

    setAnalytics({
      totalJobs,
      totalApplications,
      avgApplicationsPerJob,
      topPerformingJobs,
      applicationsByStatus,
      applicationsByDate,
      jobPerformanceMetrics
    });
  };

  // Refresh all data
  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      const isConnected = await testAPIConnection();
      if (!isConnected) {
        throw new Error('Cannot connect to backend API');
      }

      await fetchJobsWithApplications();
    } catch (err) {
      setError(`Refresh failed: ${err.message}`);
    } finally {
      setRefreshing(false);
    }
  };

  // Format date utility
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

  // Get status color helper
  const getStatusColor = (status) => {
    switch(status) {
      case 'hired': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'under_review': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'interview_scheduled': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'rejected': return 'bg-red-50 text-red-700 border-red-200';
      default: return 'bg-gray-50 text-gray-700 border-gray-200';
    }
  };

  // Component lifecycle
  useEffect(() => {
    mountedRef.current = true;
    
    const initializeAnalytics = async () => {
      setLoading(true);
      try {
        const isConnected = await testAPIConnection();
        if (!isConnected) {
          throw new Error('Cannot connect to backend API');
        }

        await fetchJobsWithApplications();
      } catch (err) {
        setError(`Analytics initialization failed: ${err.message}`);
      } finally {
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    };

    initializeAnalytics();

    // Auto-refresh every 2 minutes
    intervalRef.current = setInterval(() => {
      if (!error && !loading && !refreshing) {
        console.log('🔄 Auto-refreshing data...');
        fetchJobsWithApplications();
      }
    }, 120000);

    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Filter and sort jobs
  const filteredJobs = jobs
    .filter(job => {
      const matchesSearch = job.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           job.location.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesFilter = filterStatus === 'all' || 
                           (filterStatus === 'active' && job.applicationCount > 0) ||
                           (filterStatus === 'inactive' && job.applicationCount === 0);
      return matchesSearch && matchesFilter;
    })
    .sort((a, b) => {
      switch(sortBy) {
        case 'applications':
          return b.applicationCount - a.applicationCount;
        case 'title':
          return a.title.localeCompare(b.title);
        case 'date':
          return new Date(b.createdAt) - new Date(a.createdAt);
        case 'score':
          return b.avgScore - a.avgScore;
        default:
          return b.applicationCount - a.applicationCount;
      }
    });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
        <div className="text-center">
          <Loader className="w-12 h-12 animate-spin mx-auto text-blue-600 mb-4" />
          <h3 className="text-xl font-semibold text-gray-800 mb-2">Loading Analytics</h3>
          <p className="text-gray-600">🔄 Fetching job and application data...</p>
          <p className="text-sm text-gray-500 mt-2">Connecting to API...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 min-h-screen p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-r from-purple-500 to-blue-600 rounded-xl">
                <BarChart3 className="w-6 h-6 text-white" />
              </div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
                Job Analytics Dashboard
              </h1>
              <Activity className="w-6 h-6 text-green-500 animate-pulse" />
            </div>
            <p className="text-lg text-gray-600 max-w-2xl">
              Live analytics showing job performance and application data from your backend
            </p>
            {lastUpdated && (
              <p className="text-sm text-gray-500">
                Last updated: {lastUpdated.toLocaleTimeString()} • 
                {analytics.totalJobs} jobs • {analytics.totalApplications} applications
                <span className="ml-2 text-green-600 font-medium">● LIVE</span>
              </p>
            )}
          </div>
          
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search jobs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-3 bg-white border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm w-64"
              />
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshing || loading}
              className="px-4 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>



        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <div className="flex items-center space-x-2 mb-2">
              <AlertCircle className="w-5 h-5 text-red-500" />
              <h3 className="text-lg font-semibold text-red-800">Data Loading Error</h3>
            </div>
            <p className="text-red-700 mb-3">{error}</p>
            <button
              onClick={handleRefresh}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-xl font-medium"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* Analytics Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Jobs</p>
                <p className="text-3xl font-bold text-gray-900">{analytics.totalJobs}</p>
                <p className="text-xs text-gray-500">Active positions</p>
              </div>
              <div className="p-3 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl">
                <Briefcase className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Applications</p>
                <p className="text-3xl font-bold text-gray-900">{analytics.totalApplications}</p>
                <p className="text-xs text-gray-500">Real submissions</p>
              </div>
              <div className="p-3 bg-gradient-to-br from-green-500 to-green-600 rounded-xl">
                <Users className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg per Job</p>
                <p className="text-3xl font-bold text-gray-900">{analytics.avgApplicationsPerJob.toFixed(1)}</p>
                <p className="text-xs text-gray-500">Applications/job</p>
              </div>
              <div className="p-3 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl">
                <BarChart className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm font-medium text-gray-600">Under Review</p>
                <p className="text-3xl font-bold text-gray-900">{analytics.applicationsByStatus.under_review || 0}</p>
                <p className="text-xs text-gray-500">Pending review</p>
              </div>
              <div className="p-3 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl">
                <Clock className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        </div>

        {/* Filters and Sorting */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">Filter Jobs</label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Jobs ({jobs.length})</option>
                <option value="active">With Applications ({jobs.filter(j => j.applicationCount > 0).length})</option>
                <option value="inactive">No Applications ({jobs.filter(j => j.applicationCount === 0).length})</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">Sort By</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="applications">Application Count</option>
                <option value="title">Job Title</option>
                <option value="date">Date Created</option>
                <option value="score">Average Score</option>
              </select>
            </div>
          </div>
        </div>

        {/* Jobs with Application Details */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-6 border-b border-gray-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h3 className="text-xl font-semibold text-gray-900">Jobs & Applications</h3>
                <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
                  {filteredJobs.length} jobs • Live Data
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">
                  Total: {filteredJobs.reduce((sum, job) => sum + job.applicationCount, 0)} applications
                </span>
              </div>
            </div>
          </div>

          <div className="divide-y divide-gray-200">
            {filteredJobs.length === 0 ? (
              <div className="text-center py-12">
                <Briefcase className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h4 className="text-lg font-semibold text-gray-600 mb-2">No jobs found</h4>
                <p className="text-gray-500">Try adjusting your search or filter criteria.</p>
              </div>
            ) : (
              filteredJobs.map((job, index) => (
                <div key={job.id} className="p-6 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h4 className="text-lg font-semibold text-gray-900">{job.title}</h4>
                        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium">
                          {job.applicationCount} {job.applicationCount === 1 ? 'Application' : 'Applications'}
                        </span>
                        {job.avgScore > 0 && (
                          <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">
                            {(job.avgScore * 100).toFixed(1)}% Avg Score
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
                        <span className="flex items-center gap-1">
                          <MapPin className="w-4 h-4" />
                          {job.location}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-4 h-4" />
                          Posted {formatDate(job.createdAt)}
                        </span>
                        <span className="flex items-center gap-1">
                          <DollarSign className="w-4 h-4" />
                          {job.salaryRange}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => setSelectedJob(selectedJob === job.id ? null : job.id)}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl font-medium flex items-center gap-2 transition-colors"
                    >
                      <Eye className="w-4 h-4" />
                      {selectedJob === job.id ? 'Hide' : 'View'} Applications
                    </button>
                  </div>

                  {/* Application Status Breakdown */}
                  {Object.keys(job.statusBreakdown).length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-4">
                      {Object.entries(job.statusBreakdown).map(([status, count]) => (
                        <span
                          key={status}
                          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(status)}`}
                        >
                          {status.replace('_', ' ').toUpperCase()}: {count}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Top Candidate Preview */}
                  {job.topCandidate && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
                      <div className="flex items-center gap-2 text-green-800 text-sm">
                        <Star className="w-4 h-4" />
                        <strong>Top Candidate:</strong>
                        <span>{job.topCandidate.candidateName}</span>
                        {job.topCandidate.overallScore > 0 && (
                          <span className="bg-green-200 px-2 py-1 rounded text-xs">
                            {(job.topCandidate.overallScore * 100).toFixed(1)}% Match
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Applications List */}
                  {selectedJob === job.id && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      <h5 className="font-semibold text-gray-800 mb-3">
                        Applications ({job.applications.length})
                      </h5>
                      
                      {job.applications.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                          <Users className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                          <p>No applications yet for this position</p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {job.applications.map((app, appIndex) => (
                            <div key={app.id} className="bg-gray-50 rounded-lg p-4">
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-3">
                                  <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-semibold text-sm">
                                    {app.candidateName.split(' ').map(n => n[0]).join('')}
                                  </div>
                                  <div>
                                    <h6 className="font-medium text-gray-900">{app.candidateName}</h6>
                                    <p className="text-sm text-gray-600">{app.email}</p>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  {app.overallScore > 0 && (
                                    <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium">
                                      {(app.overallScore * 100).toFixed(1)}% Match
                                    </span>
                                  )}
                                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(app.status)}`}>
                                    {app.status.replace('_', ' ').toUpperCase()}
                                  </span>
                                </div>
                              </div>
                              
                              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                                <div>
                                  <span className="text-gray-500">Applied:</span>
                                  <span className="ml-1 text-gray-700">{formatDate(app.uploadedAt)}</span>
                                </div>
                                <div>
                                  <span className="text-gray-500">Experience:</span>
                                  <span className="ml-1 text-gray-700">{app.experienceYears} years</span>
                                </div>
                                <div>
                                  <span className="text-gray-500">File:</span>
                                  <span className="ml-1 text-gray-700">{app.filename}</span>
                                </div>
                              </div>

                              {app.matchedSkills && app.matchedSkills.length > 0 && (
                                <div className="mt-2">
                                  <span className="text-xs text-gray-500">Matched Skills:</span>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {app.matchedSkills.slice(0, 5).map((skill, skillIndex) => (
                                      <span key={skillIndex} className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">
                                        {skill}
                                      </span>
                                    ))}
                                    {app.matchedSkills.length > 5 && (
                                      <span className="text-xs text-gray-500">+{app.matchedSkills.length - 5} more</span>
                                    )}
                                  </div>
                                </div>
                              )}

                              {app.analysis && (
                                <div className="mt-2 p-2 bg-blue-50 rounded text-xs text-blue-800">
                                  <strong>AI Analysis:</strong> {app.analysis.substring(0, 150)}...
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Status Footer */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm font-medium text-gray-700">Analytics active</span>
              <span className="text-xs text-gray-500">
                Auto-refresh enabled
              </span>
            </div>
            <div className="text-sm text-gray-500">
              Connected to {API_CONFIG.BASE_URL}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FixedRealTimeAnalytics;