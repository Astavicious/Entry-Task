module AccessControl {

  class ProtectedResource {
    var authorizedUsers: set<nat>

    predicate Authorized(user: nat)
      reads this
    {
      user in authorizedUsers
    }

    constructor ()
      ensures authorizedUsers == {}
    {
      authorizedUsers := {};
    }

    method GrantAuthorization(user: nat)
      modifies this
      ensures authorizedUsers == old(authorizedUsers) + {user}
      ensures Authorized(user)
    {
      authorizedUsers := authorizedUsers + {user};
    }

    method RevokeAuthorization(user: nat)
      modifies this
      ensures authorizedUsers == old(authorizedUsers) - {user}
      ensures !Authorized(user)
    {
      authorizedUsers := authorizedUsers - {user};
    }

    method RequestAccess(user: nat) returns (granted: bool)
      ensures granted <==> user in old(authorizedUsers)
      ensures authorizedUsers == old(authorizedUsers)
    {
      granted := Authorized(user);
    }
  }
}
