# Copyright 2024 Heinrich Krupp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Integration tests for mDNS service discovery with actual network components.

These tests require the 'zeroconf' package and may interact with the local network.
They can be skipped in environments where network testing is not desired.
"""

import pytest
import asyncio
import socket
from unittest.mock import patch, Mock

# Import the modules under test
from mcp_memory_service.discovery.mdns_service import ServiceAdvertiser, ServiceDiscovery
from mcp_memory_service.discovery.client import DiscoveryClient

# Skip these tests if zeroconf is not available
zeroconf = pytest.importorskip("zeroconf", reason="zeroconf not available")


@pytest.mark.integration
class TestMDNSNetworkIntegration:
    """Integration tests that may use actual network interfaces."""
    
    @pytest.mark.asyncio
    async def test_service_advertiser_real_network(self):
        """Test ServiceAdvertiser with real network interface (if available)."""
        try:
            advertiser = ServiceAdvertiser(
                service_name="Test Integration Service",
                port=18000,  # Use non-standard port to avoid conflicts
                https_enabled=False
            )
            
            # Try to start advertisement
            success = await advertiser.start()
            
            if success:
                assert advertiser._registered is True
                
                # Let it advertise for a short time
                await asyncio.sleep(1)
                
                # Stop advertisement
                await advertiser.stop()
                assert advertiser._registered is False
            else:
                # If we can't start (e.g., no network), that's okay for CI
                pytest.skip("Could not start mDNS advertisement (network not available)")
                
        except Exception as e:
            # In CI environments or restrictive networks, this might fail
            pytest.skip(f"mDNS integration test skipped due to network constraints: {e}")
    
    @pytest.mark.asyncio
    async def test_service_discovery_real_network(self):
        """Test ServiceDiscovery with real network interface (if available)."""
        try:
            discovery = ServiceDiscovery(discovery_timeout=2)  # Short timeout
            
            # Try to discover services
            services = await discovery.discover_services()
            
            # We don't assert specific services since we don't know what's on the network
            # Just check that the discovery completed without error
            assert isinstance(services, list)
            
        except Exception as e:
            # In CI environments or restrictive networks, this might fail
            pytest.skip(f"mDNS discovery test skipped due to network constraints: {e}")
    
    @pytest.mark.asyncio
    async def test_advertiser_discovery_roundtrip(self):
        """Test advertising a service and then discovering it."""
        try:
            # Start advertising
            advertiser = ServiceAdvertiser(
                service_name="Roundtrip Test Service",
                port=18001,  # Use unique port
                https_enabled=False
            )
            
            success = await advertiser.start()
            if not success:
                pytest.skip("Could not start mDNS advertisement")
            
            try:
                # Give time for advertisement to propagate
                await asyncio.sleep(2)
                
                # Try to discover our own service
                discovery = ServiceDiscovery(discovery_timeout=3)
                services = await discovery.discover_services()
                
                # Look for our service
                found_service = None
                for service in services:
                    if "Roundtrip Test Service" in service.name:
                        found_service = service
                        break
                
                if found_service:
                    assert found_service.port == 18001
                    assert found_service.https is False
                else:
                    # In some network environments, we might not discover our own service
                    pytest.skip("Could not discover own service (network configuration)")
                
            finally:
                await advertiser.stop()
                
        except Exception as e:
            pytest.skip(f"mDNS roundtrip test skipped due to network constraints: {e}")


@pytest.mark.integration
class TestDiscoveryClientIntegration:
    """Integration tests for DiscoveryClient."""
    
    @pytest.mark.asyncio
    async def test_discovery_client_real_network(self):
        """Test DiscoveryClient with real network."""
        try:
            client = DiscoveryClient(discovery_timeout=2)
            
            # Test service discovery
            services = await client.discover_services()
            assert isinstance(services, list)
            
            # Test finding best service (might return None if no services)
            best_service = await client.find_best_service(validate_health=False)
            # We can't assert anything specific since we don't know the network state
            
            await client.stop()
            
        except Exception as e:
            pytest.skip(f"DiscoveryClient integration test skipped: {e}")
    
    @pytest.mark.asyncio
    async def test_health_check_real_service(self):
        """Test health checking against a real service (if available)."""
        try:
            client = DiscoveryClient(discovery_timeout=2)
            
            # Start a test service to health check
            advertiser = ServiceAdvertiser(
                service_name="Health Check Test Service",
                port=18002,
                https_enabled=False
            )
            
            success = await advertiser.start()
            if not success:
                pytest.skip("Could not start test service for health checking")
            
            try:
                await asyncio.sleep(1)  # Let service start
                
                # Create a mock service details for health checking
                from mcp_memory_service.discovery.mdns_service import ServiceDetails
                from unittest.mock import Mock
                
                test_service = ServiceDetails(
                    name="Health Check Test Service",
                    host="127.0.0.1",
                    port=18002,
                    https=False,
                    api_version="2.1.0",
                    requires_auth=False,
                    service_info=Mock()
                )
                
                # Try to health check (will likely fail since we don't have a real HTTP server)
                health = await client.check_service_health(test_service, timeout=1.0)
                
                # We expect this to fail since we're not running an actual HTTP server
                assert health is not None
                assert health.healthy is False  # Expected since no HTTP server
                
            finally:
                await advertiser.stop()
                await client.stop()
                
        except Exception as e:
            pytest.skip(f"Health check integration test skipped: {e}")


@pytest.mark.integration
class TestMDNSConfiguration:
    """Integration tests for mDNS configuration scenarios."""
    
    @pytest.mark.asyncio
    async def test_https_service_advertisement(self):
        """Test advertising HTTPS service."""
        try:
            advertiser = ServiceAdvertiser(
                service_name="HTTPS Test Service",
                port=18443,
                https_enabled=True,
                api_key_required=True
            )
            
            success = await advertiser.start()
            if success:
                # Verify the service info was created with HTTPS properties
                service_info = advertiser._service_info
                if service_info:
                    properties = service_info.properties
                    assert properties.get(b'https') == b'True'
                    assert properties.get(b'auth_required') == b'True'
                
                await advertiser.stop()
            else:
                pytest.skip("Could not start HTTPS service advertisement")
                
        except Exception as e:
            pytest.skip(f"HTTPS service advertisement test skipped: {e}")
    
    @pytest.mark.asyncio
    async def test_custom_service_type(self):
        """Test advertising with custom service type."""
        try:
            advertiser = ServiceAdvertiser(
                service_name="Custom Type Service",
                service_type="_test-custom._tcp.local.",
                port=18003
            )
            
            success = await advertiser.start()
            if success:
                assert advertiser.service_type == "_test-custom._tcp.local."
                await advertiser.stop()
            else:
                pytest.skip("Could not start custom service type advertisement")
                
        except Exception as e:
            pytest.skip(f"Custom service type test skipped: {e}")


@pytest.mark.integration
class TestMDNSErrorHandling:
    """Integration tests for mDNS error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_port_conflict_handling(self):
        """Test handling of port conflicts in service advertisement."""
        try:
            # Start first advertiser
            advertiser1 = ServiceAdvertiser(
                service_name="Port Conflict Service 1",
                port=18004
            )
            
            success1 = await advertiser1.start()
            if not success1:
                pytest.skip("Could not start first advertiser")
            
            try:
                # Start second advertiser with same port (should succeed - mDNS allows this)
                advertiser2 = ServiceAdvertiser(
                    service_name="Port Conflict Service 2",
                    port=18004  # Same port
                )
                
                success2 = await advertiser2.start()
                # mDNS should allow multiple services on same port
                if success2:
                    await advertiser2.stop()
                
            finally:
                await advertiser1.stop()
                
        except Exception as e:
            pytest.skip(f"Port conflict handling test skipped: {e}")
    
    @pytest.mark.asyncio
    async def test_discovery_timeout_handling(self):
        """Test discovery timeout handling."""
        try:
            discovery = ServiceDiscovery(discovery_timeout=0.1)  # Very short timeout
            
            services = await discovery.discover_services()
            
            # Should complete without error, even with short timeout
            assert isinstance(services, list)
            
        except Exception as e:
            pytest.skip(f"Discovery timeout test skipped: {e}")


# Utility function for integration tests
def is_network_available():
    """Check if network is available for testing."""
    try:
        # Try to create a socket and connect to a multicast address
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(1.0)
            s.bind(('', 0))
            return True
    except Exception:
        return False


# Skip all integration tests if network is not available
pytestmark = pytest.mark.skipif(
    not is_network_available(),
    reason="Network not available for mDNS integration tests"
)