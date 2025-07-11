#!/usr/bin/env python3
"""
Test script to verify IPv4 connection to Supabase
"""

import os
import socket
from core.config import DatabaseConfig, test_database_connection

def test_host_resolution():
    """Test how the host resolves (IPv4 vs IPv6)"""
    host = DatabaseConfig.HOST
    print(f"Testing host resolution for: {host}")
    
    try:
        # Get all addresses
        addresses = socket.getaddrinfo(host, DatabaseConfig.PORT)
        
        print("Resolved addresses:")
        for addr_info in addresses:
            family, socktype, proto, canonname, sockaddr = addr_info
            ip_version = "IPv4" if family == socket.AF_INET else "IPv6"
            ip_address = sockaddr[0]
            print(f"  {ip_version}: {ip_address}")
            
        # Check if IPv4 is available
        ipv4_addresses = [addr for addr in addresses if addr[0] == socket.AF_INET]
        if ipv4_addresses:
            print(f"\n✅ IPv4 addresses available: {len(ipv4_addresses)}")
            return True
        else:
            print("\n❌ No IPv4 addresses found")
            return False
            
    except Exception as e:
        print(f"❌ Error resolving host: {e}")
        return False

def test_connection_with_ipv4_preference():
    """Test connection with IPv4 preference enabled"""
    print("\n=== Testing with IPv4 preference ===")
    
    # Set environment variable to force IPv4
    os.environ["FORCE_IPV4"] = "true"
    
    # Test the connection
    success = test_database_connection()
    
    # Clean up
    os.environ.pop("FORCE_IPV4", None)
    
    return success

def main():
    print("=== Supabase IPv4 Connection Test ===")
    print()
    
    # Test host resolution
    has_ipv4 = test_host_resolution()
    
    if has_ipv4:
        print("\n=== Testing standard connection ===")
        standard_success = test_database_connection()
        
        if standard_success:
            print("✅ Standard connection successful")
        else:
            print("❌ Standard connection failed")
            
        # Test with IPv4 preference
        ipv4_success = test_connection_with_ipv4_preference()
        
        if ipv4_success:
            print("✅ IPv4 preference connection successful")
        else:
            print("❌ IPv4 preference connection failed")
            
        print("\n=== Summary ===")
        print(f"Standard connection: {'✅' if standard_success else '❌'}")
        print(f"IPv4 preference: {'✅' if ipv4_success else '❌'}")
        
        if not standard_success and ipv4_success:
            print("\n💡 IPv4 preference resolved the connection issue!")
            print("Add FORCE_IPV4=true to your .env file")
        elif standard_success and ipv4_success:
            print("\n✅ Both connection methods work")
        elif not standard_success and not ipv4_success:
            print("\n❌ Both connection methods failed - check your Supabase configuration")
    else:
        print("\n❌ No IPv4 addresses available for this host")

if __name__ == "__main__":
    main() 