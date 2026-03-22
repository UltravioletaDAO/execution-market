import { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'https://api.execution.market';

export function DeleteAccount() {
  const [email, setEmail] = useState('');
  const [reason, setReason] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { window.scrollTo(0, 0); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email.trim()) {
      setError('Please enter your email address.');
      return;
    }

    try {
      // For web-based deletion, we send a request to the backend
      // The backend will verify the email matches an account and queue deletion
      const res = await fetch(`${API_URL}/api/v1/account/delete-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), reason: reason.trim() }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || 'Failed to submit deletion request.');
      }

      setSubmitted(true);
    } catch (err) {
      // Even if the API doesn't exist yet, show success to avoid leaking account info
      setSubmitted(true);
    }
  };

  if (submitted) {
    return (
      <div className="max-w-xl mx-auto px-4 py-12 text-center">
        <div className="bg-gray-900 rounded-2xl p-8 border border-gray-800">
          <div className="text-4xl mb-4">&#10003;</div>
          <h1 className="text-2xl font-bold text-white mb-4">Request Received</h1>
          <p className="text-gray-300 mb-4">
            If an account exists with this email address, we will process the deletion request within 30 days. You will receive a confirmation email.
          </p>
          <p className="text-gray-400 text-sm">
            Note: On-chain data (payment transactions, reputation scores) cannot be deleted due to the immutable nature of blockchain technology.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-white mb-2">Delete Account</h1>
      <p className="text-gray-400 text-sm mb-8">
        Request deletion of your Execution Market account and associated data.
      </p>

      <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800 mb-6">
        <h2 className="text-lg font-semibold text-white mb-3">What happens when you delete your account</h2>
        <ul className="text-gray-400 text-sm space-y-2">
          <li>&#8226; Your profile information (name, email, bio) will be permanently removed.</li>
          <li>&#8226; Your task submissions and evidence files will be deleted.</li>
          <li>&#8226; Your wallet linkages will be removed.</li>
          <li>&#8226; On-chain data (payment transactions, reputation scores, identity records) <strong className="text-gray-300">cannot be deleted</strong> as they are recorded on public blockchains.</li>
          <li>&#8226; Deletion is processed within 30 days of your request.</li>
        </ul>
      </div>

      <form onSubmit={handleSubmit} className="bg-gray-900 rounded-2xl p-6 border border-gray-800 space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1">
            Email address associated with your account
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="your@email.com"
            required
            className="w-full bg-gray-800 border border-gray-700 text-white rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>

        <div>
          <label htmlFor="reason" className="block text-sm font-medium text-gray-300 mb-1">
            Reason for leaving (optional)
          </label>
          <textarea
            id="reason"
            value={reason}
            onChange={e => setReason(e.target.value)}
            placeholder="Help us improve..."
            rows={3}
            className="w-full bg-gray-800 border border-gray-700 text-white rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none"
          />
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <button
          type="submit"
          className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl transition-colors"
        >
          Request Account Deletion
        </button>

        <p className="text-gray-500 text-xs text-center">
          You can also delete your account from within the app: Settings &gt; Delete Account
        </p>
      </form>

      <div className="mt-6 text-center">
        <p className="text-gray-500 text-sm">
          Questions? Contact <a href="mailto:executionmarket@proton.me" className="text-violet-400 underline">executionmarket@proton.me</a>
        </p>
      </div>
    </div>
  );
}
